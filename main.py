import praw
from pprint import pprint
import config
import string

punctuation = string.punctuation.replace(">","").replace("=","").replace("!","").replace("/","")
punctmap = str.maketrans("","",punctuation)

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



def isSummons(comment):

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


def onQuery(query,comment):
	if(query["target"] == "post"):
		submission = comment.submission
		






commentFile = open("testComments.txt")
for line in commentFile:
	splitLine = line.split(",")
	comment = splitLine[0]
	groundTruth = splitLine[1].strip()
	parsedComment = parseComment(comment)
	valid = str(False)
	if(parsedComment != None):
		valid = str(validateComment(parsedComment))
	if(valid != groundTruth):
		print("Error:",parsedComment)
		print(line)
		print("Expected:",groundTruth)
		print("Got:",valid)
		print("-"*10)
quit()





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
	print(submission.title)
	comments = submission.comments.list() #Get all the comments from the post
	for comment in comments:
		isSummons = checkIsSummons(comment) #Check each comment to see if it is a summons
		if(isSummons):
			parseComment(comment.body)
		else:
			continue  #continue if this comment does not contain a summons
