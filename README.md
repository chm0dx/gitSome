# gitSome

## Overview

OSINT tool to extract email addresses and other useful info from various GitHub sources.

 * Provide a user account to extract email addresses associated repos
 * Provide an org account to extract email addresses associated repos
 * Provide a domain to extract related email addresses from public commits, issues, and other sources
 * Built-in FireProx to automatically create endpoints, rotate source IP, and cleanup at the end
    * Forked and modified ([chm0dx/fireprox](https://github.com/chm0dx/fireprox)) from the awesome [ustayready/fireprox](https://github.com/ustayready/fireprox)

![alt text](./gitSome_demo.gif "Quick Demo")

## Install

    git clone https://github.com/chm0dx/gitSome.git
    cd gitSome
    pip install -r requirements.txt

## Use

    usage: gitSome.py [-h] (-d DOMAIN | -u USER | -r REPO) [-t TOKEN] [-f] [-p PROXY] [-j] [-e EXCLUDE] [-fp]
                  [--secret_access_key SECRET_ACCESS_KEY] [--access_key ACCESS_KEY] [--region REGION]

    Extract email addresses and other info from various GitHub sources

    optional arguments:
      -h, --help            show this help message and exit
      -d DOMAIN, --domain DOMAIN
                            Search public commits, issues, and users for emails belonging to the provied domain.
      -u USER, --user USER  Search repos of the provided GitHub user (or org) account.
      -r REPO, --repo REPO  Search the provided GitHub repo.
      -t TOKEN, --token TOKEN
                            Authenticate searches using the given GitHub personal access token to increase rate limit and search private resources.
      -f, --forks           Include commits from forked repos.
      -p PROXY, --proxy PROXY
                            Send requests through a web or SOCKS proxy.
      -j, --json            Return full json results (as opposed to just the plaintext email).
      -e EXCLUDE, --exclude EXCLUDE
                            The name of a repo or account to exclude.
      -fp, --fireprox       Auto configure and use a FireProx endpoint. Pass in credentials or use the ~/.aws/credentials file.
      --secret_access_key SECRET_ACCESS_KEY
                            The secret access key used to create FireProx resources in AWS.
      --access_key ACCESS_KEY
                            The access key used to create FireProx resources in AWS.
      --region REGION       The AWS region to create FireProx resources in.

    Examples:
      python3 gitSome.py -d hooli.com
      python3 gitSome.py -u orgName
      python3 gitSome.py -u userName -f
      python3 gitSome.py -r userName/repoName -p http://0.0.0.0:8080
      python3 gitSome.py -u orgName -t github_pat_xxx -r excluded/repo -r excluded_account
      python3 gitSome.py -u user --fireprox
      python3 gitSome.py -d hooli.com --fireprox --access_key xxxx --secret_access_key xxxx --region us-west-2

## Disclaimer

The power is yours and so is the responsibility to understand GitHub API policies :)

![The Power is Yours](https://media.tenor.com/YMAt_1_FryQAAAAC/captain-planet-planet.gif)
