import nltk

from nltk.tokenize import sent_tokenize, word_tokenize

text = "Natural language processing is an exciting area."

print(sent_tokenize(text))

print(word_tokenize(text))

