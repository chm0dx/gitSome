import argparse
from argparse import RawTextHelpFormatter
import requests
import re

proxies = {"https":""}
auth_token = None
base_url = "https://api.github.com/"
headers = {}

class RateLimited(Exception):
	pass

class NotFound(Exception):
	pass

def process_repo(repo):
	page = 1
	results = []
	repo_url = f"{base_url}repos/{repo}"
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
				result = {"repo":repo,"name":commit["commit"][subject].get("name"),"email":commit["commit"][subject].get("email"),"login":""}
				if result.get("name") == "GitHub":
					continue
				if "noreply.github.com" in result.get("email"):
					result["email"] = ""
				if commit.get(subject) and commit.get(subject).get("login"):
					result["login"] = commit.get(subject).get("login")
				if result not in results:
					results.append(result)
		if len(commits) == 100:
			page += 1
		else:
			break
	return results


def start_from_repo(repo,proxy,fireprox):
	if fireprox:
		global base_url
		base_url = fireprox
	proxies["https"] = proxy
	results = []
	results.extend(process_repo(repo))

	return sorted(results, key=lambda result: result["repo"], reverse=True)


def start_from_account(account,forks,proxy,token,fireprox,exclusions):
	if fireprox:
		global base_url
		base_url = fireprox
	if token:
		headers["Authorization"] = f"token {token}"
	proxies["https"] = proxy
	results = []
	page = 1 
	while True:
		if account:
			repos_url = f"{base_url}users/{account}/repos?per_page=100&page={page}"
		else:
			repos_url = f"{base_url}user/repos?per_page=100&page={page}"
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


def start_from_domain(domain,proxy,fireprox):
	headers["Accept"] = "application/vnd.github.text-match+json"
	if fireprox:
		global base_url
		base_url = fireprox
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
					user_page_url = f'{base_url}users/{search_result["login"]}'
					user_page = requests.get(search_url,proxies=proxies, headers=headers).json()
					for email in re.findall(rf"([A-Za-z0-9+.]+@[\w]*{domain})",match["fragment"]):
							result = {"email":email,"source":search_result["html_url"]}
							if result not in results:
								results.append(result)

				else:
					for match in search_result["text_matches"]:
						for email in re.findall(rf"([A-Za-z0-9+.]+@[\w]*{domain})",match["fragment"]):
							result = {"email":email,"source":search_result["html_url"]}
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
  python3 gitSome.py -t github_pat_xxx -r excluded/repo -r excluded_account
  python3 gitSome.py -u user -fp fireprox_url


''',
		formatter_class=RawTextHelpFormatter)
	reqs = parser.add_mutually_exclusive_group(required=True)
	reqs.add_argument("-d","--domain",help="Search public commits, issues, and users for emails belonging to the provied domain")
	reqs.add_argument("-u","--user",help="Search repos of the provided GitHub user (or org) account")
	reqs.add_argument("-r","--repo",help="Search the provied GitHub repo")
	reqs.add_argument("-t","--token",help="Search the repos associated with the provided GitHub personal access token")
	parser.add_argument("-f","--forks",help="Include commits from forked repos",action="store_true")
	parser.add_argument("-p","--proxy",help="Send requests through a web or SOCKS proxy")
	parser.add_argument("-fp","--fireprox",help="Rewrite request URLs to use a FireProx endpoint")
	parser.add_argument("-j","--json",help="Return full json results (as opposed to just the plaintext email)", action="store_true")
	parser.add_argument("-e","--exclude",help="The name of a repo or account to exclude", action="append", default=[])
	
	args = parser.parse_args()

	try:
		if args.user or args.token:
			results = start_from_account(args.user,args.forks,args.proxy,args.token,args.fireprox,args.exclude)
		elif args.domain:
			results = start_from_domain(args.domain,args.proxy,args.fireprox)
		else:
			results = start_from_repo(args.repo,args.proxy,args.fireprox)
		
		if len(results) == 0:
			print("Didn't find anything")
		elif args.json:
			print(results)
		else:
			emails = [result for result in (set([result.get("email") for result in results if result.get("email")]))]
			[print(email) for email in sorted(emails, key=lambda x: x.split("@")[-1])]
	except RateLimited:
		print("Rate Limited :(")
	except NotFound:
		print("Not found.")
	
