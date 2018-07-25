import praw
from pprint import pprint
import config
from sqlconfig import cursor,cnx,add_submission,retrieve_submissions,update_submission,delete_submissions,purge_table
import string
import hashlib
import time

punctuation = string.punctuation.replace(">","").replace("=","").replace("!","").replace("/","")  #A list of all standard punctuation minus a few tokens that the bot searches for 
punctmap = str.maketrans("","",punctuation) #used later to filter punctuation from text
get_time_seconds = lambda: int(round(time.time())) #gets the current time in seconds

def parseComment(comment):
	"""
	Parses comment to determine what type of query to run. Does not validate the query just yet
		-comment: The body of reddit comment object
	Returns: object containing the keywords for the query
	""" 
	commentTokens = comment.lower().translate(punctmap).split() #Individual tokens/terms in comment. Remove most punctuation besides (>!=/)
	startIndex = 0 #start of query.
	try:
		startIndex = commentTokens.index("!updateme") #The index where !UpdateMe is found
	except ValueError: #if !UpdateMe is found but not as a standalone token (ie "!UpdateMe" or !!UpdateMe versu !UpdateMe)
		return None	   #then we return none, as this is an invalid query

	sliceRange = slice(startIndex,startIndex+5) #Max query should be 5 terms, ie: !UpdateMe on user in subreddit

	queryWindow = commentTokens[sliceRange] #At most, 5 tokens that comprise the query and possibly some extra text

	#pad array with None if len > 5
	lenDiff = 5 - len(queryWindow) 
	queryWindow += [None]*lenDiff 
	for i in range(1,len(queryWindow)):
		if(queryWindow[i] != None):
			queryWindow[i] = queryWindow[i].replace("!","")
	

	"""
	The summons should have the following format
	!UpdateMe [mode] [target] (in [target2])/([clause])
	Examples: !UpdateMe on user in subreddit | !UpdateMe when votes > 1000
	"""
	modes = ["on","when","help",]  #what kind of query is this?
	targets = ["op","post","all","comment"] #target can also be a username such as u/UpdatesAssistant


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
	"""
	Ensures that the query is valid. 
		-comment: the object containing the parameters from the parsed comment
	returns: True if the comment is deemed valid and false otherwise
	"""
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



def checkIfSummons(comment):
	"""
	Determines if the comment is summoning the bot. Not rigorous and functions
	just as an initial filter.
		-comment: Reddit comment object

	return: True if the comment might be a summons. False if not
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
	Determines if the token passed is a username. Simply checks if the token starts with "u/"
		-token: The potential username

	return: True if the token starts with "u/" and false otherwise.
	"""
	if(token == None):
		return False

	return token.startswith("u/")



def processRequest(parsedComment,comment):
	"""
	Sends request to the proper function to the proper handler.
		-parsedComment: the object containing the keywords from the comment
		-comment: Reddit comment object
	"""
	if(parsedComment["mode"] == "on"):
		onHandler(parsedComment,comment)


def onHandler(request,comment):
	"""
	Handler for when the user uses the "on" mode.
	Packs comment/post information into a tuple to
	dump into the sql table. A verification is then
	sent to the user.
		-request: The keywords for the !UpdateMe request
		-coment: The reddit comment object that summoned the bot
	
	"""
	print("Handling \"on\" request")
	print(request)
	if(request["target"] == "post"):
		parent = comment.submission #In this case, the parent is the originating thread
		comment_id = comment.id #the id of the requesting comment
		parent_id = parent.id #the id of the parent post
		submission_type = 0 #post
		comment_permalink = comment.permalink
		parent_permalink = parent.permalink
		body_hash = hashlib.md5(parent.selftext.encode('utf-8')).hexdigest() #hexdigest converts into string
		poster = parent.author.name
		requester = comment.author.name
		num_upvotes = parent.ups
		num_comments = parent.num_comments
		subreddit_name = parent.subreddit.display_name
		expiration_date = get_time_seconds() + 60#259200 #3 days from now
		params = (
					comment_id,parent_id,submission_type,comment_permalink,
					parent_permalink,body_hash,poster,requester,subreddit_name,
					expiration_date,num_upvotes,num_comments
					)

		reply_body = (f"Hi u/{requester}! I'll make sure to remind you about u/{poster}\'s [post](http://reddit.com{parent_permalink})!")

		addSubmissionToDatabase(params) #sends data to sql server
		replyToComment(comment,reply_body)

	if(request["target"] == "comment"):
		parent = comment.parent() #In this case, the parent is the parent comment
		comment_id = comment.id
		parent_id = parent.id
		submission_type = 1 #comment
		comment_permalink = comment.permalink
		parent_permalink = parent.permalink
		body_hash = hashlib.md5(parent.body.encode('utf-8')).hexdigest() #Gets the md5 hash of the string. Hexdigest converts into string
		poster = parent.author.name
		requester = comment.author.name
		num_upvotes = parent.ups
		num_comments = len(parent.replies)
		subreddit_name = parent.subreddit.display_name
		expiration_date = get_time_seconds() + 60#259200 #3 days from now
		params = (
					comment_id,parent_id,submission_type,comment_permalink,
					parent_permalink,body_hash,poster,requester,subreddit_name,
					expiration_date,num_upvotes,num_comments
					)

		reply_body = (f"Hi u/{requester}! I'll make sure to remind you about u/{poster}\'s [comment](https://reddit.com{parent_permalink})!")

		addSubmissionToDatabase(params) #sends data to sql server
		replyToComment(comment,reply_body)

		

def addSubmissionToDatabase(queryParams):
	"""
	Takes information and inserts them into the MySQL Database.
	Database config found in sqlconfig.py
		-queryParams: The information to be inserted into the database columns
	"""
	cursor.execute(add_submission,queryParams)
	cnx.commit()


def retrieveSubmissionsFromDatabase():
	cursor.execute(retrieve_submissions)
	submissions = []
	for submission in cursor:
		#print(user)
		submissions.append(submission)
	return submissions


def replyToComment(comment,body):
	"""
	Replies to the comment that summoned the bot. Attaches a footer to each reply from the bot
		-comment: The reddit comment object that we are replying to
		-body: The body of the reply
	"""
	if(body == None or body.strip() == ""):
		raise ValueError("Message body cannot be empty!")

	footer = ""  #Footer message for bot. Attached to every reply

	if(comment != None):
		print("Replied to comment",comment.id)
		comment.reply(body)

	else:
		raise ValueError("Comment required!")


def sendMessage(submission,body):
	"""
	Sends a message to inform the recipient that the post/comment they were following
	has been updated.
		-submission: The SQL entry of the request as a tuple.
		-body: The message body. 
	"""
	recipient = submission[8]
	subredditName = submission[9]
	postAuthor = submission[7]
	postType = getPostType(submission[3])
	footer = "" #footer for message
	subject = f"u/{postAuthor}'s {postType} in r/{subredditName} has been updated!"
	reddit.redditor(recipient).message(subject,body+footer)


def updateSubmission(submission):
	"""
	Updates the table entry with the new information.
		-submission: A tuple ocntaining all of the updated information on a query
	"""
	newSubmission = submission[:2] + submission[3:] + (submission[2],) #slice out the uid at index 2 and place it at the end (to satisfy the WHERE clause)
	cursor.execute(update_submission,newSubmission)
	cnx.commit()

def deleteSubmissions(uids):
	"""
	Deletes a table entry
		-uids: The list of uids of the rows to be deleted
	"""
	if(len(uids) == 0):
		return 
	paramInflater = ','.join(['%s'] * len(uids)) #adjusts number of inputs for query to match number of inputs passed in
	cursor.execute(delete_submissions % paramInflater,tuple(uids))
	cnx.commit()
	print("Deleted",uids)

def getPostType(typeNum):
	"""
	Converts the type number into a string for the post type
	Post: 0		Comment: 1
		-typeNum: The type number for the post type
	returns: The post type as a string
	"""
	if(typeNum == 0):
		return "post"
	elif(typeNum == 1):
		return "comment"


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
					user_agent = 'UpdatesAssistant by /u/cyclo_methane',
					username = config.dev_username,
					password = config.dev_password)

print("Initializing praw...")

bot_account = reddit.redditor("UpdatesAssistant") #This bot's reddit account

##only for test testing: 
#purge table before booting 
cursor.execute(purge_table)
cnx.commit()
##
#delete all of this bots comments before testing
for comment in bot_account.comments.new(limit=None):
	comment.delete()

#For now, we are only working with the Test Subreddit
subreddit = reddit.subreddit('UpdateBotTest')
for submission in subreddit.hot(): #get all of the posts in the subreddit
	print("Getting submission:",submission.title)
	comments = submission.comments.list() #Get all the comments from the post
	print(comments)
	for comment in comments:
		isSummons = checkIfSummons(comment) #Check each comment to see if it is a summons
		if(isSummons):
			parsedComment = parseComment(comment.body)
			valid = False
			if(parsedComment != None):
				valid = validateComment(parsedComment)
			if(valid):
				processRequest(parsedComment,comment)
			else:
				print("Not a valid query:",comment.body)
		else:
			print("Not a summons:",comment.body)
			continue  #continue if this comment does not contain a summons

while(True):
	submissions = retrieveSubmissionsFromDatabase()
	submission_uids = [] #list of uids to deleete
	for submission in submissions:  #   0           1       2     3          4           5           6      7        8        9           10          11           12
		#Submission entry columns: (requester_id,target_id,uid,type,post_permalink,parent_permalink,hash,poster,requester,subreddit,expiration_date,num_upvotes,num_comments)

		target_id = submission[1] #the id of the target submission
		oldHash = submission[6] #the old hash of the submission
		newHash = ""
		postType = getPostType(submission[3])
		if(postType == "post"):
			post = reddit.submission(target_id)
			#pprint(vars(post))
			postBody = post.selftext
			newHash = hashlib.md5(postBody.encode('utf-8')).hexdigest()
		elif(postType == "comment"):
			comment = reddit.comment(target_id)
			commentBody = comment.body
			newHash = hashlib.md5(commentBody.encode('utf-8')).hexdigest()

		if(oldHash != newHash): #compare the hashes
			#post was edited
			submission = submission[:6] + (newHash,) + submission[7:] #edit tuple to replace the old hash value
			print(submission)
			requester = submission[8]
			parent_permalink = submission[5]
			updateSubmission(submission) #Update submission with new hash.
			updateMessage = f"Hi u/{requester}! The {postType} you have been following has been updated. You can find it [here](https://reddit.com{parent_permalink})!"
			sendMessage(submission,updateMessage) #Send message that the post was updated

		expiration_date = submission[10]
		if(get_time_seconds() >= expiration_date): #when the request is passed its expiration date, stop updating requester and delete from database
			submission_uids.append(submission[2]) #uid

	deleteSubmissions(submission_uids)

