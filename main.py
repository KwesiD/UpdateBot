import praw

reddit = praw.Reddit(client_id='my client id',
					client_secret='my client secret',
					user_agent='testscript by /u/cyclo_methane')

print(reddit.read_only)