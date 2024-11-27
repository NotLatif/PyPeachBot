import asyncio
import random
import discord
import os

from config import Colors as col
from mPrint import mPrint as mp
def mPrint(tag, text):
    mp(tag, 'chessBridge', text)
	
import chessMain

if not os.path.isdir(f'{chessMain.gameRenderer.gamesFolder}'):
	os.mkdir(f'{chessMain.gameRenderer.gamesFolder}')

def num2emoji(num : int):
	words = []
	for digit in str(num):
		if digit == '0': words.append('zero')
		elif digit == '1': words.append('one')
		elif digit == '2': words.append('two')
		elif digit == '3': words.append('three')
		elif digit == '4': words.append('four')
		elif digit == '5': words.append('five')
		elif digit == '6': words.append('six')
		elif digit == '7': words.append('seven')
		elif digit == '8': words.append('eight')
		elif digit == '9': words.append('nine')
		else: words.append('?')
	return f':{"::".join(words)}:'

def getGameWinnerName(players, score) -> str:
	if score[0] == score[1]:
		return "Pareggio"
	return str(players[0]) if score[0]>score[1] else str(players[1])

async def loadGame(threadChannel : discord.Thread, bot, players : list[discord.Member], fetchThread : tuple[discord.Message, discord.Embed], selectedBoard : tuple[str,str], designName : str = 'default'):
	"""links bot.py with chess game (Main.py)
		
		:param threadChannel: the thread where the bot will send messages about the game.
		:param bot: the discord bot client.
		:param players: the chess game players(`discord.Member`) IN THIS ORDER > `[black, white]`
		:param fetchThread: list containing `[the message that created the thread, the embed of the message]`
	"""
	"""TODO
	- Mini database of games won / games lost
	- keep track also of scores between players
		-eg:	("luigi", "Mario", 23, 25) -> meaning that of all the game played between luigi VS mario ever
												luigi won 23 times and mario won 25 times									
	- keep track of move history between different rounds and don't delete them after each one (maybe also store them in the mini database
	"""
	
	solitare = True if players[0] == players[1] else False
	score = [0, 0]
	round = 0
	emojis = ('🌑', '⚪') #('🖤', '🤍') (black, white) 	< order matters
#	players  [black, white] because: players[False] -> Black, players[True] -> White
# 									useful for using with gs.whiteMoves
	if not os.path.isdir(f'{chessMain.gameRenderer.gamesFolder}{threadChannel.guild.id}'):
		os.mkdir(f'{chessMain.gameRenderer.gamesFolder}{threadChannel.guild.id}')

	chessGame = chessMain.ChessGame(f'{threadChannel.guild.id}/{threadChannel.id}', players, threadChannel.guild.name, round)
	gs = chessMain.Engine.GameState(chessGame)

	while True: #matchloop (iterates every round)
		round += 1
		if(selectedBoard[0] == 'FEN'):
			gs.boardFromFEN(selectedBoard[1])
		elif(selectedBoard[0] == 'BOARD'):
			gs.boardFromFEN(chessGame.boards[selectedBoard[1]])
		else:
			await threadChannel.send('Error has occurred chessBridge.FENNotFound')
			return -1
		chessGame.FEN = gs.getFEN()

		renderer = chessMain.gameRenderer.GameRenderer(chessGame, designName, gs)
		
		roundFEN = gs.getFEN()
		mPrint('GAME', f'FEN {roundFEN}')

		didIllegalMove = [False, ''] #[bool, str]
		boardMessages = ['placeholder'] #needed to delete the last edited board and avoid chat clutter
							#this will keep max two boards loaded at a time [board0, board1]
							#will delete the last -> [board1, board2]


		while True: #gameloop (iterates every turn)
			turn = gs.whiteMoves #if turn = 1, players[turn] is white, if turn = 0 players[turn is black]
#									 turn = True						  turn = False

			lastTurn = not gs.whiteMoves #If true when checkmate/stalemate, white has won

			#generate board and moves
			if not didIllegalMove[0]: #no need to regenerate if last move was illegal
				validMoves = gs.getValidMoves()#will check below in the code for illegal moves
				renderer.drawBoard()#IMPORTANT draw the board after getting the moves (to draw checks and moves on the board)

			#send board img to discord
			with open(chessGame.getOutputFile(), "rb") as fh:
				f = discord.File(fh, filename=chessGame.getOutputFile())
				boardMessages.append(await threadChannel.send(file=f))
				if boardMessages[0] != 'placeholder':
					await boardMessages[0].delete() #delete last board
				del boardMessages[0] #remove last board from list -> the current one will be at boardMessages[0]
			
		#MACRO TASK: ask for a move or command
			#1. make an embed with the request
			embed = discord.Embed(
				title= f'Fai una mossa {str(players[turn])[:-5]}!',
				description = '''
					Scrivi in chat posizione iniziale e posizione finale del pedone
					e.g.: A2A4\n
					scrivi "undo" per annullare l'ultima mossa
					scrivi "stop" per fermare la partita
					scrivi "board" per rigenerare l'immagine della scacchiera
					scrivi "draw" per offrire un pareggio
					scrivi "surrender" se vuoi arrenderti
				''',
				color = col.white if (turn == 1) else col.black
			)
			
			#2a. if previous move was illegal modify the embed with the info
			if didIllegalMove[0]:
				embed.title = 'Mossa non valida'
				embed.description += f'\n{didIllegalMove[1]}'
				embed.color = col.red

				didIllegalMove = [False, '']
			
			#2b. if previous move resulted in check modify the embed with the info
			elif gs.inCheck: #using elif, because last move cannot be illegal, so if it is, the player currently in check made an illegal move and should be notified
				embed.title = 'Scacco!'
				embed.description = 'Fai una mossa per difendere il tuo Re'
				embed.color = col.orange

			embed.set_footer(text=f'È il turno di {players[turn]} {emojis[turn]}')#I'm too good at this shit #godcomplex

			#2c. GAMEOVER SCRIPT if checkmate or stalemate modify the embed and end the game
			async def roundOverActions(reason : str, players : list[discord.Member], rematchMsg : discord.Message):
				winner = players[lastTurn] #winner is whoever had the turn BEFORE the current one
				
				if reason != 'DRAW':
					# Printing the result of the game.
					mPrint('GAME', f'Game won by {winner}, <gameID:{threadChannel.id}>')

					pgn = gs.getPGN()
					await threadChannel.send(f"```{pgn}```")

					#edit and send the main channel embed
					embed = fetchThread[1]
					embed.title = f'{reason}\n{emojis[0]} {players[0]} {num2emoji(score[0])} :vs: {num2emoji(score[1])} {players[1]} {emojis[1]}'
					embed.description = f'Match winner: {str(winner)[:-5]} {emojis[lastTurn]}\nOverall winner: {f"{getGameWinnerName(players, score)}"}'
					embed.set_footer(text=f'ID: {threadChannel.id}, now voting for rematch...')
					embed.color = col.white if lastTurn == 1 else col.black 
					await fetchThread[0].edit(embed=embed)
				
				else:
					pgn = gs.getPGN()
					await threadChannel.send(f"```{pgn}```")

					#edit and send the main channel embed
					embed = fetchThread[1]
					embed.title = f'Pareggio!'
					embed.set_footer(text=f'ID: {threadChannel.id}, now voting for rematch...')
					embed.color = col.white if lastTurn == 1 else col.black 
					await fetchThread[0].edit(embed=embed)

				#ask for another round
				reactions = ('⛔', '✅')
				await rematchMsg.add_reaction(reactions[0])
				await rematchMsg.add_reaction(reactions[1])
				
				votingPlayers = list(players) # < one of the few times learning things in school saved ma A LOT of time 
				#								for who does not know votingPlayers = players is a reference (like an alias)
				#								here I am writing things like people will look at my repo 😢

				async def notEnoughVotes():
					newThreadName = f'GG, {str(players[0])[:-5]} {score[0]}-VS-{score[1]} {str(players[1])[:-5]}'
					embed = discord.Embed(
						title = 'Non Hanno votato abbastanza giocatori.',
						color = col.red
					)
					await rematchMsg.edit(embed = embed)
					
					embed.title = f'-- GAME OVER --\n{emojis[0]} {players[0]} {num2emoji(score[0])} :vs: {num2emoji(score[1])} {players[1]} {emojis[1]}'
					embed.color = col.white if players[lastTurn] else col.black
					embed.set_footer(text=f'ID: {threadChannel.id} game concluded')
					await fetchThread[0].edit(embed=embed)
					await threadChannel.edit(name = f'{newThreadName}', reason=reason, locked=True, archived=True)
				
				def rematchVoteCheck(reaction, user): #check if the different reactions are from different user (and not one user reacting 2 times)
					mPrint('DEBUG', f'CHECK1, {user}, {[v.id for v in votingPlayers]}')
					if user in votingPlayers:
						votingPlayers.remove(user)
						return str(reaction.emoji) in reactions and user != bot.user
					return False

				try:
					r1, temp = await bot.wait_for('reaction_add', timeout=30.0, check=rematchVoteCheck)
					
					r2, temp = await bot.wait_for('reaction_add', timeout=30.0, check=rematchVoteCheck)
				except asyncio.TimeoutError:
					await notEnoughVotes()
					return 0
				else:
					del temp # don't really need it
					mPrint('DEBUG', f'reactions: {r1} {r2} == {reactions[1]}')
					if r1.emoji == reactions[1] and r2.emoji == reactions[1]: #both votes are yes
						mPrint('INFO', 'will rematch')
						newEmbedTitle = f'{emojis[0]} {players[0]} {num2emoji(score[0])} :vs: {num2emoji(score[1])} {players[1]} {emojis[1]}'
						newThreadName = f'{str(players[0])[:-5]} {score[0]}-VS-{score[1]} {str(players[1])[:-5]}'
						
						embed = discord.Embed(
							title = 'Rivincita!',
							description= newThreadName,
							color = col.green
						)
						embed.set_footer(text = "Generating rematch... please wait!")
						await rematchMsg.edit(embed = embed)

						embed = fetchThread[1]
						embed.title = f'*Generating rematch...*\n{newEmbedTitle}'
						embed.color = col.orange
						embed.set_footer(text=f'ID: {threadChannel.id}')
						await fetchThread[0].edit(embed=embed)

						#switch players
						p = players[0]
						players[0] = players[1]
						players[1] = p

						s = score[0]
						score[0] = score[1]
						score[1] = s

						await asyncio.sleep(random.randrange(2, 5))
						#await threadChannel.edit(name=newThreadName) #BUG game halts after 3rd round?

						embed.title = f'Round {score[0] + score[1] + 1}\n{emojis[0]} {players[0]} {num2emoji(score[0])} :vs: {num2emoji(score[1])} {players[1]} {emojis[1]}'
						embed.color = col.green
						await fetchThread[0].edit(embed=embed)
						return 1
					else:
						await notEnoughVotes()
						return 0

			if gs.checkMate:
				chessGame.result = "1-0" if lastTurn else "0-1"
				score[lastTurn] += 1
				embed.title = 'CHECKMATE!'
				embed.description = f'Congratulazioni {players[lastTurn]} {emojis[lastTurn]}'
				embed.color = col.white if lastTurn == 1 else col.black 
				embed.set_footer(text='Rivincita? (vota entro 30 secondi)')
				rematchMsg = await threadChannel.send(embed=embed)
				resp = await roundOverActions('CHECKMATE', players, rematchMsg)
				if(resp):
					#rematch
					break
				else:
					#gameOver
					return
				 
			elif gs.staleMate:
				chessGame.result = "1-0" if lastTurn else "0-1"
				score[lastTurn] += 1
				embed.title = 'Stalemate!'
				embed.description = f'Congratulazioni {players[lastTurn]}'
				embed.color = col.white if lastTurn == 1 else col.black
				embed.set_footer(text='Rivincita? (vota entro 30 secondi)')
				rematchMsg = await threadChannel.send(embed=embed)
				resp = await roundOverActions('Stalemate!', players, rematchMsg)
				if(resp):
					#rematch
					break
				else:
					#gameOver
					return 
			
			elif gs.draw:
				#ask for opponent to accept draw
				embed.title = 'Pareggio!'
				embed.color = col.aqua
				embed.set_footer(text='Rivincita? (vota entro 30 secondi)')
				rematchMsg = await threadChannel.send(embed=embed)
				chessGame.result = "1/2-1/2"
				resp = await roundOverActions('DRAW', players, rematchMsg)
				if(resp):
					#rematch
					break
				else:
					#gameOver
					return 
			
			#3. send the embed
			inputAsk = await threadChannel.send(embed=embed)

			#4. a little stupid but loop until get a good message (from the right player)
			validInput = False
			command = ''
			while not validInput: #input loop
				#a. await for input
				def check(m):	#check if message was sent in thread using ID
					return m.channel.id == threadChannel.id and m.author in players

				userMessage = await bot.wait_for('message', check=check)

				#b. process commands that can be made by both players at any point in the game
				if(userMessage.content == "stop"):
					#send embed to thread
					embed = discord.Embed(title='❌ Partita annullata ❌')
					pgn = gs.getPGN()
					#edit and send the main channel embed
					embed = fetchThread[1]
					embed.title = f'-- GAME OVER --\n{emojis[0]} {players[0]} {num2emoji(score[0])} :vs: {num2emoji(score[1])} {players[1]} {emojis[1]}'
					embed.description = f'❌ Partita annullata ❌\nOverall winner: {getGameWinnerName(players, score)}'
					embed.color = col.red
					embed.set_footer(text=f'ID: {threadChannel.id}')
					await fetchThread[0].edit(embed=embed)
					await threadChannel.send(f"```{pgn}```")
					await threadChannel.send(embed=embed)
					await threadChannel.edit(reason='Partita annullata', locked=True, archived=True)
					mPrint('GAME', f'Game stopped by user, <gameID:{threadChannel.id}, user:{userMessage.author}>')
					mPrint('GAME', f'Game stats: <{gs.getStats()}>')
					return -1
				
				elif(userMessage.content == "undo"): #TODO last turn must confirm undo (won't do for now idc)
					gs.undoMove()
					break
			
				elif(userMessage.content == "board"):
					break

				elif(userMessage.content == "draw"):
					reactions = ('⛔', '✅')
					embed = discord.Embed(
						title=f"{userMessage.author} Ha offerto un pareggio, reagisci per accettare o rifiutare"
					)
					drawMessage = await threadChannel.send(embed=embed)
					await drawMessage.add_reaction(reactions[0])
					await drawMessage.add_reaction(reactions[1])
					def drawVoteCheck(emoji, user):
						return user != bot.user and emoji.emoji in reactions and (user != userMessage.author or solitare)
					try:
						emoji, player = await bot.wait_for('reaction_add', timeout=25.0, check=drawVoteCheck)
					except asyncio.TimeoutError:
						embed.title = "Pareggio rifiutato."
						await drawMessage.edit(embed=embed)
						await drawMessage.clear_reactions()
						continue
					else:
						if emoji.emoji == reactions[1]:
							chessGame.result = '1/2-1/2'
							gs.draw = True
							break
						else:
							embed.title = "Pareggio rifiutato."
							await drawMessage.edit(embed=embed)
							await drawMessage.clear_reactions()
							continue
						
				#c. check if message author has the turn
				if turn == 1 and userMessage.author == players[1]: #avoid players making moves for the opposite team
					validInput = True #out of the input loop
				elif turn == 0 and userMessage.author == players[0]: 
					validInput = True
				else:
					await userMessage.delete()
			
			#5. delete the embed to avoid clutter
			await inputAsk.delete()
			mPrint("USER", f'{userMessage.author}, comando: {userMessage.content}')

			if(userMessage.content in ['undo', 'board']):
				continue
			
		#MACRO TASK: parse user input
			#1. create distinction between input (str) and message (discord.Message)
			userMove = userMessage.content

			#2. Detect if user wants to perform a command
			#		Commands below here can only be performed by the player that has the turn
			if(userMove == "command"): #ctrl-z
				pass
			
			#3. Parse user input
			userMove = userMove.replace('/', '').replace(',','').replace(' ','').lower()
			mPrint('DEBUG', f'userMove: {userMove}')
			if userMove == 'kg1': userMove = "O-O"
			if userMove == 'kg8': userMove = "O-O"
			if userMove == 'kc1': userMove = "O-O-O"
			if userMove == 'kc8': userMove = "O-O-O"

		#MACRO TASK: move the pieces

			#1. check input type
			if (len(userMove) == 4 and #this should be enough
				userMove[0] in 'abcdefgh' and userMove[2] in 'abcdefgh' and 
				userMove[1] in '12345678' and userMove[3] in '12345678'): #Move is type A2A2
			
				#a. create a structure to hold the data 	
				userMove = [#omg this is so confusing wth #impostorsyndrome
					#                       rank (1->8)                              file (A->H)
					(chessMain.Engine.Move.ranksToRows[userMove[1]], chessMain.Engine.Move.filesToCols[userMove[0]]),
					(chessMain.Engine.Move.ranksToRows[userMove[3]], chessMain.Engine.Move.filesToCols[userMove[2]])
				]
				
				#b. send the move to the engine for elaboration
				move = chessMain.Engine.Move(userMove[0], userMove[1], gs.board)
				mPrint("USER", userMove)
			
			else: #move was probably written in algebraic notation
				mPrint('DEBUG', 'parsing algebraic')
				move = chessMain.Engine.Move.findMoveFromAlgebraic(userMove, validMoves)
				mPrint('INFO', f'Correspondence found: {move}')

			moveMade = False
			#2. detect if move is valid
			for i in range(len(validMoves)):
				if move == validMoves[i]:
					mPrint("GAME", f"Valid move: {move.getChessNotation()}")
					gs.makeMove(validMoves[i]) #play the move generated by the engine
					moveMade = True
			if not moveMade:	
				#if move was not made then
				#3F. if move is invalid notify the user and ask again for input
				didIllegalMove = [True, f'Illegal move {userMove}']
				await userMessage.delete()
				mPrint("GAMEErr", "Invalid move.")
				mPrint("GAME", f"your move: {userMove}")


def getBoards() -> dict[str, str]:
	return chessMain.getSavedBoards()

def doesBoardExist(board : str) -> bool:
	return chessMain.doesBoardExist(board)

def getBoardImgPath(board, id) -> tuple[str]:
	"""
	Returns a tuple with
	(filepath, filename)
	"""
	mPrint('DEBUG', f'RENDERING {board}')
	return chessMain.renderBoard(board, id)