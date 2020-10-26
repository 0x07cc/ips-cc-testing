#!/usr/bin/env python3
# ips-cc Testing Script. Run it in a Docker container.
import sys
import subprocess
import os
import socket
import time
import threading
import re

# Parameters
nfqueue = 33
testPort = 2222
forbiddenWord = "CC{test}"

lightBlue = '\033[1;34m'
lightCyan = '\033[1;36m'
lightGreen = '\033[1;32m'
red = '\033[0;31m'
noColor = '\033[0m'
passedTests = 0
failedTests = 0

# Function that outputs the given text in green
# if it contains a useful message.
def testOK(string):
    if len(string.strip()) > 0:
        print(f"{lightGreen}{string}{noColor}")
    global passedTests
    passedTests += 1

# Function that outputs the given text in red
# if it contains a useful message.
def testKO(string):
    if len(string.strip()) > 0:
        print(f"{red}{string}{noColor}")
    global failedTests
    failedTests += 1

# Function that prints the command output if successful,
# otherwise it prints the return code.
def runCommand(cmdList):
    process = subprocess.run(cmdList, stdout=subprocess.PIPE, timeout=5)
    if process.returncode == 0:
        testOK(process.stdout.decode().rstrip("\n"))
    else:
        cmdString = " ".join(cmdList)
        testKO(f"Error executing '{cmdString}' Code: {process.returncode}")

# Function that executes a nc client to localhost,
# sending the provided string and then closing the connection.
# Note that the Busybox nc does not have -q option.
def startNetcatClient(string):
    # Sleep because the client starts before the server
    time.sleep(0.5)
    ncCommand = ('nc', '-q', '1', '127.0.0.1', str(testPort))
    echo = subprocess.Popen(('echo', f'{string}'), stdout=subprocess.PIPE)
    try:
        subprocess.check_output(ncCommand, stdin=echo.stdout, timeout=5)
    except subprocess.TimeoutExpired:
        testKO("Error while sending test string: netcat client timeout")
        # TODO possibile problema: regola IPTABLES si ma IPS OFF
    return

# Function that executes "iptables -L -n", parses its output,
# searches for the NFQUEUE entries and returns them in a dictionary.
def getRules():
    # Retrieving iptables rules
    cmdList = ["iptables", "-L", "-n"]
    process = subprocess.run(cmdList, stdout=subprocess.PIPE, timeout=5)
    if process.returncode == 0:
        iptables_list = process.stdout.decode()
    else:
        testKO("iptables rules listing Error")
        return {}

    # Parsing Output
    rules = {}
    lines = iptables_list.split("\n")
    nfqueueRules = []
    strToFind = "NFQUEUE num " + str(nfqueue)

    for line in lines:
        if line.find(strToFind) != -1:
            nfqueueRules.append(line)

    for riga2 in nfqueueRules:
        found = re.search("spt:(\d)+", riga2)
        if found is not None:
            porta = int(riga2[found.start() + 4:found.end()])
            rules[porta] = "OUTPUT"
        else:
            found = re.search("dpt:(\d)+", riga2)
            if found is not None:
                porta = int(riga2[found.start() + 4:found.end()])
                rules[porta] = "INPUT"
            else:
                testKO("Error while parsing iptables rules list")
    return rules


print(f"{lightBlue}IPS Testing Script\n")

# Root privileges
if os.geteuid() != 0:
    testKO("Script not started as root. Aborting.")
    testKO("This script is meant to be executed in a container!")
    exit(-1)

# Python Version
version = sys.version.split("\n")[0]
versionNumber = version[0:3]
print(f"{lightCyan}python3  version: {noColor}", end="")
if float(versionNumber) >= 3.8:
    testOK(version)
else:
    testKO(version)

# iptables Version
print(f"{lightCyan}iptables version: {noColor}", end="")
runCommand(["iptables", "--version"])

# Checking if NetfilterQueue is installed
try:
    from netfilterqueue import NetfilterQueue
    testOK("NetfilterQueue module installed")
except ModuleNotFoundError:
    testKO("NetfilterQueue module not installed. Aborting.")
    # exit(-1)

# Current iptables rules: checking if is there a rule for the chosen port.
rules = getRules()
if len(rules) == 0:
    testOK("No iptables rules found")
else:
    if rules.get(testPort) is None:
        testOK(f"No iptables rules matching port {testPort}")
    else:
        testKO(f"iptables rule matching port {testPort} found!")

# Tests without IPS
print(f"{lightCyan}Testing communication without IPS: {noColor}")

# Starting the receiver server with listening timeout
server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
server.settimeout(3)
try:
    server.bind(("0.0.0.0", testPort))
    server.listen(10)
except OSError:
    testKO("Binding error. Aborting.")
    exit(-1)

for test in range(1, 6):
    stringToSend = "IPS-Testing-Script-" * 2 * test

    # Starting the client before the server blocking method
    ncThread = threading.Thread(target=startNetcatClient, args=(stringToSend,))
    ncThread.start()

    # Server blocking method (with timeout)
    try:
        clientsocket, addr = server.accept()

        receivedBytes = clientsocket.recv(1024)
        clientsocket.close()

        if receivedBytes.decode().rstrip("\n") == stringToSend:
            testOK(f"Test string received (length: {len(stringToSend)})")
        else:
            testKO(f"Wrong test string received (length: {len(stringToSend)})")
    except (socket.timeout, ConnectionResetError):
        testKO(f"Test string not received (length: {len(stringToSend)})")

    time.sleep(0.3)

# Adding the iptables rule
print(f"{lightCyan}Adding an iptables rule: {noColor}", end="")
runCommand(['iptables', '-I', 'INPUT', '-j', 'NFQUEUE', '--queue-num', '33',
            '-p', 'tcp', '--dport', str(testPort)])

# Testing if the rule exists
rules = getRules()
if len(rules) != 0:
    if rules.get(testPort) is None:
        testKO("Fail")
    else:
        testOK("Success!")
else:
    testKO("Fail")

# Checking if the IPS executable exists
if not os.path.isfile('/root/ips-cc/main.py'):
    testKO("ips-cc main.py not found in /root/ips-cc/")
else:
    print(f"{lightCyan}Starting IPS: {noColor}", end="")
    # Starting IPS from a temp directory, to avoid saving logs and
    # "dropped packets" files in the git directory.
    ipsCommand = ['/usr/bin/env', 'python3', '/root/ips-cc/main.py']
    tempDir = '/var/tmp/'
    ipsProc = subprocess.Popen(ipsCommand, stdout=subprocess.PIPE, cwd=tempDir)

    # Checking if it is running
    if ipsProc.poll() is None:
        testOK("Success!")
    else:
        testKO("Fail")

    # Tests with IPS
    print(f"{lightCyan}Testing communication with IPS: {noColor}")

    # Tests with permitted words
    for goodTest in range(1, 6):
        stringToSend = "IPS-Testing-Script-" * 2 * goodTest

        # Starting the client before the server blocking method
        ncThread = threading.Thread(target=startNetcatClient,
                                    args=(stringToSend,))
        ncThread.start()

        # Server blocking method (with timeout)
        try:
            clientsocket, addr = server.accept()

            receivedBytes = clientsocket.recv(1024)
            clientsocket.close()

            if receivedBytes.decode().rstrip("\n") == stringToSend:
                testOK(f"Test string received (length: {len(stringToSend)})")
            else:
                testKO("Wrong test string received (length: "
                       + str(len(stringToSend)) + ")")
        except (socket.timeout, ConnectionResetError):
            testKO(f"Test string not received (length: {len(stringToSend)})")

        time.sleep(0.3)

    # Tests with forbidden words
    for badTest in range(1, 6):
        stringToSend = f"IPS-{forbiddenWord}-Script-" * 2 * badTest

        # Starting the client before the server blocking method
        ncThread = threading.Thread(target=startNetcatClient,
                                    args=(stringToSend,))
        ncThread.start()

        # Server blocking method (with timeout)
        try:
            clientsocket, addr = server.accept()

            receivedBytes = clientsocket.recv(1024)
            clientsocket.close()

            if receivedBytes.decode().rstrip("\n") == stringToSend:
                testKO("Test string containing forbidden words received"
                       + f" (length: {len(stringToSend)})")
            else:
                testKO("Wrong test string received (length: "
                       + str(len(stringToSend)) + ")")
        except (socket.timeout, ConnectionResetError):
            testOK(f"Test string containing forbidden words not received"
                   + f" (length: {len(stringToSend)})")

        time.sleep(0.3)

    # Stopping the receiver server
    server.close()

    # Sending SIGINT to the IPS Process to kill it and verifying its status.
    print(f"{lightCyan}Shutting down IPS: {noColor}", end="")
    ipsProc.send_signal(2)
    time.sleep(0.5)
    if ipsProc.poll() == 0:
        testOK("Success!")
    else:
        testKO("Fail")

print(f"{lightCyan}Removing the iptables rule{noColor}")
runCommand(['iptables', '-D', 'INPUT', '1'])

# Summary of the results
totalTests = passedTests + failedTests
resultColor = red + "⚠️  "
if passedTests == totalTests:
    resultColor = lightGreen
resultString = f"Passed Tests: {resultColor}{passedTests} of {totalTests}"
print(f"{lightCyan}{resultString}{noColor}")
