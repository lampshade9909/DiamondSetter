import sys
from Libraries.hash import Hash
from Libraries.set import Set

doHash = False
doSet = False

if len(sys.argv) == 3 and sys.argv[1].lower() == 'hash':
    doHash = True
elif len(sys.argv) == 2 and sys.argv[1].lower() == 'set':
    doSet = True
else:
    print('Improper usage.  Try this:')
    print('     python diamondSetter.py hash <textToHash>')
    print('     python diamondSetter.py set')

if doHash:
    myText = str(sys.argv[2]).strip()
    Hash(myText)

if doSet:
    Set()
