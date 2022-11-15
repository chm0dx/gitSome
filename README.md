# gitSome

gitSome extract email addresses and other info from various GitHub sources

## Install

    git clone https://github.com/chm0dx/gitSome.git
    cd gitSome
    pip install -r requirements.txt

## Use

    usage: gitSome.py [-h] (-d DOMAIN | -u USER | -r REPO | -t TOKEN) [-f] [-p PROXY] [-fp FIREPROX] [-j] [-e EXCLUDE]

    Extract email addresses and other info from various GitHub sources

    optional arguments:
      -h, --help            show this help message and exit
      -d DOMAIN, --domain DOMAIN
                            Search public commits, issues, and users for emails belonging to the provied domain
      -u USER, --user USER  Search repos of the provided GitHub user (or org) account
      -r REPO, --repo REPO  Search the provied GitHub repo
      -t TOKEN, --token TOKEN
                            Search the repos associated with the provided GitHub personal access token
      -f, --forks           Include commits from forked repos
      -p PROXY, --proxy PROXY
                            Send requests through a web or SOCKS proxy
      -fp FIREPROX, --fireprox FIREPROX
                            Rewrite request URLs to use a FireProx endpoint
      -j, --json            Return full json results (as opposed to just the plaintext email)
      -e EXCLUDE, --exclude EXCLUDE
                            The name of a repo or account to exclude

    Examples:
      python3 gitSome.py -d hooli.com
      python3 gitSome.py -u orgName
      python3 gitSome.py -u userName -f
      python3 gitSome.py -r userName/repoName -p http://0.0.0.0:8080
      python3 gitSome.py -t github_pat_xxx -r excluded/repo -r excluded_account
      python3 gitSome.py -u user -fp fireprox_url

## Disclaimer

The power is yours and so is the responsibility to understand GitHub API policies :)

![The Power is Yours](https://media.tenor.com/YMAt_1_FryQAAAAC/captain-planet-planet.gif)
