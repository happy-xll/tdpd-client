import sys
import time

program_message = \
    '''
{0}
'''


def display_message():
    message = program_message.format('\n'.join(sys.argv[1:])).split('\n')
    for line in message:
        print(line)
