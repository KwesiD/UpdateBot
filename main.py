import praw
from pprint import pprint
import config
from sqlconfig import cursor,cnx,add_submission
import string
import hashlib
import time

punctuation = string.punctuation.replace(">","").replace("=","").replace("!","").replace("/","")
punctmap = str.maketrans("","",punctuation)
get_time_seconds = lambda: int(round(time.time() * 1000)) #gets the current time in seconds

def parseComment(comment):
	"""
	Parses comment to determine what type of query to run. Does not validate the query just yet
		-comment: The body of reddit comment object
	Returns: object containing the keywords for the query
	"""
	commentTokens = comment.lower().translate(punctmap).split() #Individual tokens/terms in comment

	startIndex = 0
	try:
		startIndex = commentTokens.index("!updateme") #The index where !UpdateMe is found
	except ValueError:
		return None

	sliceRange = slice(startIndex,startIndex+5) #Max query should be 5 terms, ie: !UpdateMe on user in subreddit

	queryWindow = commentTokens[sliceRange] #At most, 5 tokens that comprise the query and possibly some extra text

	#pad array with None if len > 5
	len_diff = 5 - len(queryWindow) 
	queryWindow += [None]*len_diff 
	
	"""
	The summons should have the following format
	!UpdateMe [mode] [target] (in [target2])/([clause])
	Examples: !UpdateMe on user in subreddit | !UpdateMe when votes > 1000
	"""
	modes = ["on","when","help",]
	targets = ["op","post","all","comment"] #target1 can also be a username such as u/UpdatesAssistant


	mode = None
	target = None
	hasIn = False
	target2 = None
	clause = None
	if(queryWindow[1] in modes): #Checks mode
		mode = queryWindow[1]
		if(mode == "on"):
			if(queryWindow[2] in targets or isUser(queryWindow[2])): #checks target
				target = queryWindow[2]
				if(queryWindow[3] == "in" and queryWindow[4] == "subreddit"): #checks for in-statement
					hasIn = True
					target2 = queryWindow[4]

		elif(mode == "when"):
			mode = queryWindow[1]
			operators = [">",">="]
			if(queryWindow[2] != None and queryWindow[3] != None and queryWindow[4] != None): #if clause is delimited by whitespace
				if(queryWindow[3] in operators):
					clause = (queryWindow[2],queryWindow[3],queryWindow[4])

			elif(queryWindow[2] != None and queryWindow[3] == None): #if clause is not delimited by white space
				for operator in operators:
					if(operator in queryWindow[2]):
						splitToken = queryWindow[2].split(operator)
						clause = (splitToken[0],operator,splitToken[1])
						break

		elif(mode == "help"):
			mode = queryWindow[1]

	return {"mode":mode,"target":target,"hasIn":hasIn,"target2":target2,"clause":clause}

	
def validateComment(comment):
	mode = comment["mode"]
	target = comment["target"]
	target2 = comment["target2"]
	hasIn = comment["hasIn"]
	clause = comment["clause"]
	if(mode != None):
		if(mode == "on" and target == None):
			return False
		elif((mode == "when" and hasIn == True and target2 == None) or (mode == "when" and clause == None)):
			return False
		return True
	else:
		return False



def check_if_summons(comment):

	"""
	Determines if the comment is summoning the bot
		-comment: Reddit comment object

	return: True if the comment is a summons. False if not
	"""

	#Summons must start with !UpdateMe
	if(comment.author.fullname == bot_account.fullname): #Return false if the comment was posted by this bot
		return False 
	if("!updateme" in comment.body.lower()):
		return True
	else:
		return False 



#TODO: Make this a little more rigorous using reddit's api to determine if the user even exists
def isUser(token):
	"""
	Determines if the token passed is a username
	Simply checks if the token starts with "u/"
		-token: The potential username

	return: True if the token starts with "u/" and false otherwise.
	"""
	if(token == None):
		return False

	return token.startswith("u/")



def processRequest(parsedComment,comment):
	if(parsedComment["mode"] == "on"):
		onQuery(parsedComment,comment)

def onQuery(query,comment):
	if(query["target"] == "post"):
		parent = comment.submission #In this case, the parent is the originating thread
		# pprint(vars(comment))
		# pprint(vars(parent))
		comment_id = comment.id
		comment_type = 0 #post
		comment_permalink = comment.permalink
		parent_permalink = parent.permalink
		body_hash = hashlib.md5(parent.selftext.encode('utf-8')).hexdigest() #hexdigest converts into string
		poster = parent.author.name
		requester = comment.author.name
		num_upvotes = parent.ups
		num_comments = parent.num_comments
		expiration_date = get_time_seconds() + 259200 #3 days from now
		params = (
			comment_id,comment_type,comment_permalink,
					parent_permalink,body_hash,poster,requester,
					expiration_date,num_upvotes,num_comments
					)
		add_submission_to_database(params)
		

def add_submission_to_database(query_params):
	cursor.execute(add_submission,query_params)
	cnx.commit()


# #Initialize PRAW
# reddit = praw.Reddit(client_id = config.client_id,
# 					client_secret = config.client_secret,
# 					user_agent = 'testscript by /u/cyclo_methane',
# 					username = config.dev_username,
# 					password = config.dev_password)

# subreddit = reddit.subreddit('UpdateBotTest')
# for submission in subreddit.hot(): #get all of the posts in the subreddit
# 	pprint(vars(submission))
# 	quit()



# commentFile = open("testComments.txt")
# for line in commentFile:
# 	splitLine = line.split(",")
# 	comment = splitLine[0]
# 	groundTruth = splitLine[1].strip()
# 	parsedComment = parseComment(comment)
# 	valid = str(False)
# 	if(parsedComment != None):
# 		valid = str(validateComment(parsedComment))
# 	if(valid != groundTruth):
# 		print("Error:",parsedComment)
# 		print(line)
# 		print("Expected:",groundTruth)
# 		print("Got:",valid)
# 		print("-"*10)
# quit()





#Initialize PRAW
reddit = praw.Reddit(client_id = config.client_id,
					client_secret = config.client_secret,
					user_agent = 'testscript by /u/cyclo_methane',
					username = config.dev_username,
					password = config.dev_password)

bot_account = reddit.redditor("UpdatesAssistant") #This bot's reddit account


#For now, we are only working with the Test Subreddit
subreddit = reddit.subreddit('UpdateBotTest')
for submission in subreddit.hot(): #get all of the posts in the subreddit
	#print(submission.title)
	comments = submission.comments.list() #Get all the comments from the post
	for comment in comments:
		isSummons = check_if_summons(comment) #Check each comment to see if it is a summons
		if(isSummons):
			parsedComment = parseComment(comment.body)
			valid = False
			if(parsedComment != None):
				valid = validateComment(parsedComment)
			if(valid):
				processRequest(parsedComment,comment)
		else:
			continue  #continue if this comment does not contain a summons



# {'_comments_by_id': {},
#  '_fetched': False,
#  '_flair': None,
#  '_info_params': {},
#  '_mod': None,
#  '_reddit': <praw.reddit.Reddit object at 0x037D3E10>,
#  'approved': False,
#  'approved_at_utc': None,
#  'approved_by': None,
#  'archived': False,
#  'author': Redditor(name='cyclo-methane'),
#  'author_flair_background_color': None,
#  'author_flair_css_class': None,
#  'author_flair_richtext': [],
#  'author_flair_template_id': None,
#  'author_flair_text': None,
#  'author_flair_text_color': None,
#  'author_flair_type': 'text',
#  'banned_at_utc': None,
#  'banned_by': None,
#  'can_gild': True,
#  'can_mod_post': True,
#  'category': None,
#  'clicked': False,
#  'comment_limit': 2048,
#  'comment_sort': 'best',
#  'content_categories': None,
#  'contest_mode': False,
#  'created': 1532181513.0,
#  'created_utc': 1532152713.0,
#  'distinguished': None,
#  'domain': 'self.UpdateBotTest',
#  'downs': 0,
#  'edited': False,
#  'gilded': 0,
#  'hidden': False,
#  'hide_score': False,
#  'id': '90n7sw',
#  'ignore_reports': False,
#  'is_crosspostable': False,
#  'is_original_content': False,
#  'is_reddit_media_domain': False,
#  'is_self': True,
#  'is_video': False,
#  'likes': None,
#  'link_flair_css_class': None,
#  'link_flair_richtext': [],
#  'link_flair_text': None,
#  'link_flair_text_color': 'dark',
#  'link_flair_type': 'text',
#  'locked': False,
#  'media': None,
#  'media_embed': {},
#  'media_only': False,
#  'mod_note': None,
#  'mod_reason_by': None,
#  'mod_reason_title': None,
#  'mod_reports': [],
#  'name': 't3_90n7sw',
#  'no_follow': True,
#  'num_comments': 4,
#  'num_crossposts': 0,
#  'num_reports': 0,
#  'over_18': False,
#  'parent_whitelist_status': None,
#  'permalink': '/r/UpdateBotTest/comments/90n7sw/test1/',
#  'pinned': False,
#  'post_categories': None,
#  'pwls': None,
#  'quarantine': False,
#  'removal_reason': None,
#  'removed': False,
#  'report_reasons': [],
#  'rte_mode': 'markdown',
#  'saved': False,
#  'score': 1,
#  'secure_media': None,
#  'secure_media_embed': {},
#  'selftext': '',
#  'selftext_html': None,
#  'send_replies': True,
#  'spam': False,
#  'spoiler': False,
#  'stickied': False,
#  'subreddit': Subreddit(display_name='UpdateBotTest'),
#  'subreddit_id': 't5_m3b6p',
#  'subreddit_name_prefixed': 'r/UpdateBotTest',
#  'subreddit_subscribers': 1,
#  'subreddit_type': 'private',
#  'suggested_sort': None,
#  'thumbnail': 'self',
#  'thumbnail_height': None,
#  'thumbnail_width': None,
#  'title': 'Test1',
#  'ups': 1,
#  'url': 'https://www.reddit.com/r/UpdateBotTest/comments/90n7sw/test1/',
#  'user_reports': [],
#  'view_count': None,
#  'visited': False,
#  'whitelist_status': None,
#  'wls': None}