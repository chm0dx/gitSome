import argparse
import json
import random
import re
import requests
import shutil
import subprocess

from bs4 import BeautifulSoup
from pathlib import Path

try:
    from .fireprox import fire
except ImportError:
    from fireprox import fire


proxies = {"https":""}
auth_token = None
base_url = "https://api.github.com/"
headers = {}
alerts = []
fp_id = None
recon_repo = "gitSome_recon"

def process_repo(repo,max_commits):
	page = 1
	commits_processed = 0
	max_hit = False
	results = []
	repo_url = f"{base_url}repos/{repo}"
	repo_html_url = f"https://github.com/{repo}"
	
	while True:
		commits_url = f'{repo_url}/commits?per_page=100&page={page}'
		r = requests.get(commits_url,proxies=proxies,headers=headers)
		
		commits = r.json()

		if isinstance(commits,dict) and "API rate limit exceeded" in commits.get("message"):
			raise Exception("Rate Limited :( Wait, connect to a different network, or provide a proxy.")
		elif isinstance(commits,dict) and commits.get("message") == 'Git Repository is empty.':
			return []
		elif r.status_code != 200:
			raise Exception(f'Failed to retrieve commits ({r.json().get("message")})')
		
		for commit in commits:
			for subject in ["author","committer"]:
				result = {"repo":repo_html_url,"name":commit["commit"][subject].get("name"),"email":commit["commit"][subject].get("email").lower(),"login":""}
				if result.get("name") == "GitHub":
					continue
				if "noreply.github.com" in result.get("email"):
					result["email"] = ""
				if commit.get(subject) and commit.get(subject).get("html_url"):
					login = commit.get(subject).get("html_url")
					if login == "https://github.com/invalid-email-address":
						login = ""
					result["login"] = login
				if result not in results:
					results.append(result)
				commits_processed += 1
				if commits_processed == max_commits:
					max_hit = True
					print(f"\nHit max commit limit for repo: {repo_html_url}")
					break
		if len(commits) == 100 and not max_hit:
			page += 1
		else:
			break
	return results


def start_from_repo(repo,proxy,token,max_commits):
	if token:
		headers["Authorization"] = f"token {token}"
	proxies["https"] = proxy
	results = []
	results.extend(process_repo(repo,max_commits))

	return sorted(results, key=lambda result: result["repo"], reverse=True)


def start_from_account(account,forks,proxy,token,exclusions,max_commits):
	if token:
		headers["Authorization"] = f"token {token}"
	proxies["https"] = proxy
	results = []
	org = ""

	try:
		account_url = f"https://github.com/{account}"
		r = requests.get(account_url)
		soup = BeautifulSoup(r.text,"lxml")
		social_card = soup.select(".vcard-details")
		if social_card:
			socials = [link.get("href") for link in social_card[0].select(".Link--primary")]
			results.append({"repo":"","login":account_url,"socials":socials})
		org_card = soup.select(".orghead")
		if org_card:
			social_links = soup.select(".orghead")[0].select(".Link--primary")
			if social_links:
				socials = []
				for social_link in social_links:
					if social_link.get("href").endswith("/followers"):
						continue
					if "mailto:" in social_link.get("href"):
						results.append({"repo":"","login":account_url,"email":social_link.get("href").replace("mailto:","")})
					else:
						socials.append(social_link.get("href"))
				if socials:
					results.append({"repo":"","login":account_url,"socials":socials})
	except Exception as ex:
		alerts.append(f"Couldn't get accounts socials ({ex})")

	members_url = f"{base_url}orgs/{account}/members"
	r = requests.get(members_url,proxies=proxies, headers=headers)
	if r.status_code not in [200,404]:
		raise Exception(f"Failed to retrieve account info ({r.json().get('message')})")
	if r.status_code == 200:
		members = r.json()
		if isinstance(members,list):
			org = account
			org_html_url = f"https://github.com/{account}"
			results.append({"org":org_html_url, "repo":""})
			for member in members:
				login = member.get("html_url")
				if login == "https://github.com/invalid-email-address":
					login = ""
				results.append({"login":member.get("html_url"), "repo":"", "org":org_html_url})
	orgs_url = f"{base_url}users/{account}/orgs"
	r = requests.get(orgs_url,proxies=proxies, headers=headers)
	orgs = r.json()
	if r.status_code not in [200,404]:
		raise Exception(f"Failed to retrieve account info ({r.json().get('message')})")
	if r.status_code == 200:
		if isinstance(orgs,list):
			for user_org in orgs:
				results.append({"org":f'https://github.com/{user_org.get("login")}', "repo":""})

	page = 1 
	while True:

		if org:
			repos_url = f"{base_url}orgs/{account}/repos?per_page=100&page={page}"
		else:
			repos_url = f"{base_url}users/{account}/repos?per_page=100&page={page}"
		repos = requests.get(repos_url,proxies=proxies, headers=headers).json()

		if isinstance(repos,dict) and "API rate limit exceeded" in repos.get("message"):
			raise Exception("Rate Limited :( Wait, connect to a different network, or provide a proxy.")
		if isinstance(repos,dict) and "Not Found" in repos.get("message"):
			raise Exception("Couldn't find the starting object. Check that the user/org/repo exists.")

		for repo in repos:
			if not forks and repo["fork"]:
				results.append({"repo":repo["html_url"]})
				continue
			if any(exclusion in repo["full_name"] for exclusion in exclusions):
				continue
			results.extend(process_repo(repo["full_name"],max_commits))
		if len(repos) == 100:
			page +=1
		else:
			break

	return sorted(results, key=lambda result: result["repo"], reverse=True)


def start_from_domain(domain,proxy,token,max_commits):
	headers["Accept"] = "application/vnd.github.text-match+json"
	if token:
		headers["Authorization"] = f"token {token}"
	proxies["https"] = proxy
	results = []
	page = 1
	
	for search_field in ["issues","commits","users"]:
		while True:
			search_url = f'{base_url}search/{search_field}?q="{domain}"&per_page=100&page={page}'
			r = requests.get(search_url,proxies=proxies, headers=headers)
			search_results = r.json()

			if search_results.get("message") and "API rate limit exceeded" in search_results.get("message"):
				raise Exception("Rate Limited :( Provide a token to increase limits, wait, connect to a different network, or provide a proxy.")
			if search_results.get("message") and "Not Found" in search_results.get("message"):
				raise Exception("Couldn't find the starting object. Check that the user/org/repo exists.")
			elif r.status_code != 200:
				raise Exception(f"Failed initiating GitHub search ({r.json().get('message')})")

			for search_result in search_results["items"]:
				if search_field == "users":
					login = search_result["html_url"]
					if login == "https://github.com/invalid-email-address":
						login = ""
					if login:
						results.append({"login":search_result["html_url"], "repo":""})

					user_page_url = f'{base_url}users/{search_result["login"]}'
					r = requests.get(search_url,proxies=proxies, headers=headers)
					user_page = r.json()

					if search_results.get("message") and "API rate limit exceeded" in search_results.get("message"):
						raise Exception("Rate Limited :( Provide a token to increase limits, wait, connect to a different network, or provide a proxy.")
					elif r.status_code != 200:
						raise Exception(f"Failed initiating GitHub search ({r.json().get('message')})")

					for match in search_result["text_matches"]:
						for email in re.findall(rf"((?<!\\)[A-Za-z0-9+.]+@[\w]*{domain})",match["fragment"]):
								print(search_result)
								result = {"email":email.lower(),"source":search_result["html_url"], "repo":""}
								if result not in results:
									results.append(result)
				else:
					for match in search_result["text_matches"]:
						for email in re.findall(rf"((?<!\\)[A-Za-z0-9+.]+@[\w]*{domain})",match["fragment"]):
							result = {"email":email.lower(),"source":search_result["html_url"], "repo":"/".join(search_result["url"].replace("api.","").replace("repos/","").split("/")[0:5])}
							if result not in results:
								results.append(result)
			if len(search_results) == 100:
				page +1
			else:
				break
	page = 1
	return results

def start_from_emails(emails,proxy,token,max_commits):

	proxies["https"] = proxy
	results = []
	headers = {"Authorization":f"Bearer {token}"}
	existing_remote = False
	user_and_repo = ""
	remote_ssh = ""
	data = {"name":f"{recon_repo}", "private":True}

	r = requests.post("https://api.github.com/user/repos", headers=headers, data=json.dumps(data))
	if r.status_code == 422 and r.json().get("errors")[0].get("message") == "name already exists on this account":
		existing_remote = True
		r = requests.get("https://api.github.com/user/repos", headers=headers)
		for result in r.json():
			if result.get("name") == recon_repo:
				user_and_repo = result.get("full_name")
				remote_ssh = result.get("ssh_url")
	elif r.status_code != 201:
		raise Exception(f'Failed to create GitHub repo ({r.json().get("message")})')
	else:
		user_and_repo = r.json().get("full_name")
		remote_ssh = r.json().get("ssh_url")

	if (Path(f"./{recon_repo}/.git")).is_dir():
		shutil.rmtree(Path(f"./{recon_repo}"))

	if existing_remote:
		output = subprocess.run(f"git clone {remote_ssh}", shell=True, capture_output=True)
		if output.returncode != 0 and output.stderr:
			raise Exception(output.stderr.decode())
	else:
		output = subprocess.run(f"git init ./{recon_repo}", shell=True, capture_output=True)
		if output.returncode != 0 and output.stderr:
			raise Exception(output.stderr.decode())
		output = subprocess.run(f"git -C ./{recon_repo}/ remote add origin {remote_ssh}", shell=True, capture_output=True)
		if output.returncode != 0 and output.stderr:
			raise Exception(output.stderr.decode())

	if len(list(Path(f"./{recon_repo}").iterdir())) == 1:
		output = subprocess.run(f"echo '' > ./{recon_repo}/empty && git -C ./{recon_repo}/ add . && git -C ./{recon_repo}/ commit -m 'init' && git -C ./{recon_repo}/ push --set-upstream origin master", shell=True, capture_output=True)

	for index, email in enumerate(emails):
		branch = f"branch{index}"
		output = subprocess.run(f"git -C ./{recon_repo}/ checkout -b {branch}", shell=True, capture_output=True)
		if output.returncode != 0 and output.stderr:
			raise Exception(output.stderr.decode())
		output = subprocess.run(f"echo '{index}' >> ./{recon_repo}/empty && git -C ./{recon_repo}/ add . && git -C ./{recon_repo}/ commit -m 'test' --author 'gitSome <{email}>'", shell=True, capture_output=True)
		if output.returncode != 0 and output.stderr:
			raise Exception(output.stderr.decode())
		output = subprocess.run(f"git -C ./{recon_repo}/ push origin {branch}", shell=True, capture_output=True)
		if output.returncode != 0 and output.stderr:
			raise Exception(output.stderr.decode())
		r = requests.get(f"https://api.github.com/repos/{user_and_repo}/branches/{branch}", headers=headers)
		author = r.json().get("commit").get("author")
		if author:
			login = author.get('html_url')
			if login == "https://github.com/invalid-email-address":
				login = ""
			result = {"email":email.lower(),"login":login}
			results.append(result)
		#output = subprocess.run(f"git -C ./{recon_repo}/ checkout master", shell=True, capture_output=True)
		#output = subprocess.run(f"git -C ./{recon_repo}/ branch -D {branch}", shell=True, capture_output=True)
		#output = subprocess.run(f"git -C ./{recon_repo}/ push origin -d {branch}", shell=True, capture_output=True)
		
		if output.returncode != 0 and output.stderr:
			print(output.returncode)
			alerts.append(output.stderr.decode())
			#raise Exception(output.stderr.decode())

	r = requests.delete(f"https://api.github.com/repos/{user_and_repo}", headers=headers)
	if r.status_code == 403:
		alerts.append(f"The provided token does not have the delete_repo scope. The temporary repo {user_and_repo} will have to be deleted manually here: https://github.com/{user_and_repo}/settings.")
	shutil.rmtree(Path(f"./{recon_repo}"))

	return results


if __name__ == "__main__":
	parser = argparse.ArgumentParser(
		description = "Extract email addresses and other info from various GitHub sources",
		epilog = '''
Examples:
  python3 gitSome.py -d hooli.com
  python3 gitSome.py -u orgName
  python3 gitSome.py -u userName
  python3 gitSome.py -e gavbel@hooli.io,baghead@hooli.io -t token
  python3 gitSome.py -r userName/repoName -p http://0.0.0.0:8080
  python3 gitSome.py -u orgName -t github_pat_xxx -r ignored/repo -r ignored_account
  python3 gitSome.py -u user --fireprox
  python3 gitSome.py -d hooli.com --fireprox --access_key xxxx --secret_access_key xxxx --region us-west-2


''',
	formatter_class=argparse.RawTextHelpFormatter)
	reqs = parser.add_mutually_exclusive_group(required=True)
	reqs.add_argument("-d","--domain", help="Search public commits, issues, and users for emails belonging to the provied domain.")
	reqs.add_argument("-u","--user", help="Search repos of the provided GitHub user (or org) account.")
	reqs.add_argument("-r","--repo", help="Search the provided GitHub repo.")
	reqs.add_argument("-e","--emails", help="File or comma-separated list of emails to convert into GitHub accounts. Requires an API token, SSH access to GitHub, and git deployed locally.")
	parser.add_argument("-t","--token", help="Authenticate searches using the given GitHub personal access token to increase rate limit, search private resources, and allow for email-to-account conversion.")
	parser.add_argument("-f","--forks", help="Include commits from forked repos.", action="store_true")
	parser.add_argument("-p","--proxy", help="Send requests through a web or SOCKS proxy.")
	parser.add_argument("-j","--json", help="Return full json results (as opposed to just the plaintext email).", action="store_true")
	parser.add_argument("-i","--ignore", help="The name of a repo or account to ignore.", action="append", default=[])
	parser.add_argument("-fp","--fireprox", help="Auto configure and use a FireProx endpoint. Pass in credentials or use the ~/.aws/credentials file.", action="store_true")
	parser.add_argument("--secret_access_key", required=False, help="The secret access key used to create FireProx resources in AWS.")
	parser.add_argument("--access_key", required=False, help="The access key used to create FireProx resources in AWS.")
	parser.add_argument("--region", required=False, help="The AWS region to create FireProx resources in.")
	parser.add_argument("--max_commits", required=False, help="Max number of commits to analyze per repo. Defaults to 1000.", default=1000, type=int)
	args = parser.parse_args()
	

	try:
		if not args.access_key and args.secret_access_key:
			raise Exception("When providing keys, provide both an access key and a secret access key.")
		if args.emails and not args.token:
			raise Exception("-e/--emails requires a GitHub access token to be passed in with -t/--token.")
		if args.fireprox:
			print("\nSetting up FireProx...")
			fp = fire.FireProx(access_key=args.access_key, secret_access_key=args.secret_access_key, region=args.region)
			base_url = re.search(r"=> (.*) ", fp.create_api(base_url))[1]
			fp_id = base_url.replace("https://","").split(".")[0]
			random_url = '.'.join(str(random.randint(0,255)) for _ in range(4))
			headers["X-My-X-Forwarded-For"] = random_url
		if args.user:
			print("\nAnalyzing account...")
			results = start_from_account(args.user,args.forks,args.proxy,args.token,args.ignore, args.max_commits)
		elif args.domain:
			print("\nSearching for domain matches...")
			results = start_from_domain(args.domain,args.proxy,args.token, args.max_commits)
		elif args.emails:
			if Path(args.emails).is_file():
				with open(args.emails,"r") as file:
					emails = file.read().splitlines()
			else:
				emails = [email.strip() for email in args.emails.split(",")]
			print(f"\nGitting, commiting, and reviewing for {len(emails)} email{'s' if len(emails) > 1 else ''}...")
			results = start_from_emails(emails,args.proxy,args.token, args.max_commits)
		else:
			print("\nAnalyzing repo...")
			results = start_from_repo(args.repo,args.proxy,args.token, args.max_commits)
		
		if len(results) == 0:
			print("\nDidn't find any results in public data.")
		elif args.json:
			print()
			print(results)
		else:
			if args.emails:
				print()
				print(f"Users ({len(results)}):")
				for result in results:
					print(f'\t{result.get("login")} ({result.get("email")})')
			else:
				emails = [result for result in (set([result.get("email") for result in results if result.get("email")]))]
				repos = [result for result in (set([result.get("repo") for result in results if result.get("repo")]))]
				logins = [login for login in (set([result.get("login") for result in results if result.get("login")]))]
				orgs = [org for org in (set([result.get("org") for result in results if result.get("org")]))]
				socials = list(set(sum([result.get("socials") for result in results if result.get("socials")],[])))
				print()
				if repos:
					print(f"Repos ({len(repos)}):")
					[print(f"\t{repo}") for repo in sorted(repos)]
				if logins:
					print(f"Users ({len(logins)}):")
					[print(f"\t{login}") for login in sorted(logins)]
				if orgs:
					print(f"Orgs ({len(orgs)}):")
					[print(f"\t{org}") for org in sorted(orgs)]
				if emails:
					print(f"Emails ({len(emails)}):")
					[print(f"\t{email}") for email in sorted(emails, key=lambda x: x.split("@")[-1])]
				if socials:
					print(f"Socials ({len(socials)})")
					[print(f"\t{social}") for social in sorted(socials)]

	except Exception as ex:
		print(f"\nERROR: {ex}")
		
	if fp_id:
		fp.delete_api(fp_id)
	if (Path(f"./{recon_repo}/.git")).is_dir():
		shutil.rmtree(Path(f"./{recon_repo}"))
	if alerts:
		print()
		for alert in alerts:
			print(f"ALERT: {alert}")

	print()
