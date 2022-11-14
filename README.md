# gitSome

gitSome analyzes GitHub repo commits and extracts email, name, and user information.

## Install

    git clone https://github.com/chm0dx/gitSome.git
    cd gitSome
    pip install -r requirements.txt

## Use

    usage: gitSome.py [-h] (-u USER | -r REPO | -t TOKEN) [-f] [-p PROXY] [-fp FIREPROX] [-j]
                  [-e EXCLUDE]

    Pull emails, names, and usersnames from GitHub repo commits.

    optional arguments:
      -h, --help            show this help message and exit
      -u USER, --user USER  The name of a GitHub user or org account
      -r REPO, --repo REPO  The name of a GitHub repo
      -t TOKEN, --token TOKEN
                            Analyze the repos associated with a GitHub personal access token
      -f, --forks           Include commits from forked repos
      -p PROXY, --proxy PROXY
                            Send requests through a web or SOCKS proxy
      -fp FIREPROX, --fireprox FIREPROX
                            Rewrite request URLs to use a FireProx endpoint
      -j, --json            Return full json of email, name, & account (as opposed to just the plaintext email)
      -e EXCLUDE, --exclude EXCLUDE
                            The name of a repo or account to exclude

    Examples:
      python3 gitSome.py -u orgName
      python3 gitSome.py -u userName -f
      python3 gitSome.py -r userName/repoName -p http://0.0.0.0:8080
      python3 gitSome.py -t github_pat_xxx -r excluded/repo -r excluded_account
      python3 gitSome.py -u user -d hooli.com -fp fireprox_url

## Disclaimer

The power is yours and so is the responsibility to understand GitHub API policies :)
![The Power is Yours](https://media.tenor.com/YMAt_1_FryQAAAAC/captain-planet-planet.gif)
