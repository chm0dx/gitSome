import argparse
import random
import re
import requests

from fireprox import fire

proxies = {"https":""}
auth_token = None
base_url = "https://api.github.com/"
headers = {}

class RateLimited(Exception):
	pass

class NotFound(Exception):
	pass

class IncompleteKeys(Exception):
	pass

def process_repo(repo):
	page = 1
	results = []
	repo_url = f"{base_url}repos/{repo}"
	repo_html_url = f"https://github.com/{repo}"
	while True:
		commits_url = f'{repo_url}/commits?per_page=100&page={page}'
		commits = requests.get(commits_url,proxies=proxies,headers=headers).json()
		if isinstance(commits,dict) and "API rate limit exceeded" in commits.get("message"):
			raise RateLimited()
		if isinstance(commits,dict) and commits.get("message") == 'Git Repository is empty.':
			return []
		if isinstance(commits,dict) and "Not Found" in commits.get("message"):
			raise NotFound()
		for commit in commits:
			for subject in ["author","committer"]:
				result = {"repo":repo_html_url,"name":commit["commit"][subject].get("name"),"email":commit["commit"][subject].get("email"),"login":""}
				if result.get("name") == "GitHub":
					continue
				if "noreply.github.com" in result.get("email"):
					result["email"] = ""
				if commit.get(subject) and commit.get(subject).get("html_url"):
					result["login"] = commit.get(subject).get("html_url")
				if result not in results:
					results.append(result)
		if len(commits) == 100:
			page += 1
		else:
			break
	return results


def start_from_repo(repo,proxy,token):
	if token:
		headers["Authorization"] = f"token {token}"
	proxies["https"] = proxy
	results = []
	results.extend(process_repo(repo))

	return sorted(results, key=lambda result: result["repo"], reverse=True)


def start_from_account(account,forks,proxy,token,exclusions):
	if token:
		headers["Authorization"] = f"token {token}"
	proxies["https"] = proxy
	results = []
	page = 1 
	while True:
		members_url = f"{base_url}orgs/{account}/members"
		members = requests.get(members_url,proxies=proxies, headers=headers).json()
		if isinstance(members,list):
			for member in members:
				results.append({"login":member.get("html_url"), "repo":""})
		orgs_url = f"{base_url}users/{account}/orgs"
		orgs = requests.get(orgs_url,proxies=proxies, headers=headers).json()
		if isinstance(orgs,list):
			for org in orgs:
				results.append({"org":org.get("html_url"), "repo":""})
		if account:
			repos_url = f"{base_url}users/{account}/repos?per_page=100&page={page}"
		repos = requests.get(repos_url,proxies=proxies, headers=headers).json()

		if isinstance(repos,dict) and "API rate limit exceeded" in repos.get("message"):
			raise RateLimited()
		if isinstance(repos,dict) and "Not Found" in repos.get("message"):
			raise NotFound()

		for repo in repos:
			if not forks and repo["fork"]:
				continue
			if any(exclusion in repo["full_name"] for exclusion in exclusions):
				continue
			results.extend(process_repo(repo["full_name"]))
		if len(repos) == 100:
			page +=1
		else:
			break

	return sorted(results, key=lambda result: result["repo"], reverse=True)


def start_from_domain(domain,proxy,token):
	headers["Accept"] = "application/vnd.github.text-match+json"
	if token:
		headers["Authorization"] = f"token {token}"
	proxies["https"] = proxy
	results = []
	page = 1
	
	for search_field in ["issues","commits","users"]:
		while True:
			search_url = f'{base_url}search/{search_field}?q="{domain}"&per_page=100&page={page}'
			search_results = requests.get(search_url,proxies=proxies, headers=headers).json()

			if search_results.get("message") and "API rate limit exceeded" in search_results.get("message"):
				raise RateLimited()
			if search_results.get("message") and "Not Found" in search_results.get("message"):
				raise NotFound()

			for search_result in search_results["items"]:
				if search_field == "users":
					results.append({"login":search_result["html_url"], "repo":""})
					user_page_url = f'{base_url}users/{search_result["login"]}'
					user_page = requests.get(search_url,proxies=proxies, headers=headers).json()
					for email in re.findall(rf"((?<!\\)[A-Za-z0-9+.]+@[\w]*{domain})",match["fragment"]):
							result = {"email":email.lower(),"source":search_result["html_url"], "repo":"/".join(search_result["url"].replace("api.","").replace("repos/","").split("/")[0:5])}
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

if __name__ == "__main__":
	parser = argparse.ArgumentParser(
		description = "Extract email addresses and other info from various GitHub sources",
		epilog = '''
Examples:
  python3 gitSome.py -d hooli.com
  python3 gitSome.py -u orgName
  python3 gitSome.py -u userName -f
  python3 gitSome.py -r userName/repoName -p http://0.0.0.0:8080
  python3 gitSome.py -u orgName -t github_pat_xxx -r excluded/repo -r excluded_account
  python3 gitSome.py -u user --fireprox
  python3 gitSome.py -d hooli.com --fireprox --access_key xxxx --secret_access_key xxxx --region us-west-2


''',
	formatter_class=argparse.RawTextHelpFormatter)
	reqs = parser.add_mutually_exclusive_group(required=True)
	reqs.add_argument("-d","--domain", help="Search public commits, issues, and users for emails belonging to the provied domain.")
	reqs.add_argument("-u","--user", help="Search repos of the provided GitHub user (or org) account.")
	reqs.add_argument("-r","--repo", help="Search the provided GitHub repo.")
	parser.add_argument("-t","--token", help="Authenticate searches using the given GitHub personal access token to increase rate limit and search private resources.")
	parser.add_argument("-f","--forks", help="Include commits from forked repos.", action="store_true")
	parser.add_argument("-p","--proxy", help="Send requests through a web or SOCKS proxy.")
	parser.add_argument("-j","--json", help="Return full json results (as opposed to just the plaintext email).", action="store_true")
	parser.add_argument("-e","--exclude", help="The name of a repo or account to exclude.", action="append", default=[])
	parser.add_argument("-fp","--fireprox", help="Auto configure and use a FireProx endpoint. Pass in credentials or use the ~/.aws/credentials file.", action="store_true")
	parser.add_argument("--secret_access_key", required=False, help="The secret access key used to create FireProx resources in AWS.")
	parser.add_argument("--access_key", required=False, help="The access key used to create FireProx resources in AWS.")
	parser.add_argument("--region", required=False, help="The AWS region to create FireProx resources in.")
	args = parser.parse_args()
	if not args.access_key and args.secret_access_key:
		raise IncompleteKeys()

	try:
		if args.fireprox:
			fp = fire.FireProx(access_key=args.access_key, secret_access_key=args.secret_access_key, region=args.region)
			base_url = re.search(r"=> (.*) ", fp.create_api(base_url))[1]
			fp_id = base_url.replace("https://","").split(".")[0]
			random_url = '.'.join(str(random.randint(0,255)) for _ in range(4))
			headers["X-My-X-Forwarded-For"] = random_url
		else:
			fp_id = None
		if args.user:
			results = start_from_account(args.user,args.forks,args.proxy,args.token,args.exclude)
		elif args.domain:
			results = start_from_domain(args.domain,args.proxy,args.token)
		else:
			results = start_from_repo(args.repo,args.proxy,args.token)
		
		if len(results) == 0:
			print("Didn't find any results in public data.")
		elif args.json:
			print(results)
		else:
			emails = [result for result in (set([result.get("email") for result in results if result.get("email")]))]
			repos = [result for result in (set([result.get("repo") for result in results if result.get("repo")]))]
			logins = [login for login in (set([result.get("login") for result in results if result.get("login")]))]
			orgs = [org for org in (set([result.get("org") for result in results if result.get("org")]))]
			if emails:
				print(f"Emails ({len(emails)}):")
				[print(f"\t{email}") for email in sorted(emails, key=lambda x: x.split("@")[-1])]
			if repos:
				print(f"Repos ({len(repos)}):")
				[print(f"\t{repo}") for repo in sorted(repos)]
			if logins:
				print(f"Users ({len(logins)}):")
				[print(f"\t{login}") for login in sorted(logins)]
			if orgs:
				print(f"Orgs ({len(orgs)}):")
				[print(f"\t{org}") for org in sorted(orgs)]
	except RateLimited:
		print("Rate Limited :( Wait, connect to a different network, or provide a proxy.")
	except NotFound:
		print("Couldn't find the starting object. Check that the user/org/repo exists.")
	except IncompleteKeys:
		print("When providing keys, provide both an access key and a secret access key.")
	except KeyboardInterrupt:
		print("\nCleaning up...")
	if fp_id:
		fp.delete_api(fp_id)
