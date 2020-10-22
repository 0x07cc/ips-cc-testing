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

lightBlue = '\033[1;34m'
lightCyan = '\033[1;36m'
lightGreen = '\033[1;32m'
red = '\033[0;31m'
noColor = '\033[0m'
passedTests = 0
failedTests = 0

# Function that outputs the given text in green
def testOK(string):
    print(f"{lightGreen}{string}{noColor}")
    global passedTests
    passedTests += 1

# Function that outputs the given text in red
def testKO(string):
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
            porta = int(riga2[found.start()+4:found.end()])
            rules[porta] = "OUTPUT"
        else:
            found = re.search("dpt:(\d)+", riga2)
            if found is not None:
                porta = int(riga2[found.start()+4:found.end()])
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
socket.setdefaulttimeout(5)
server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
try:
    server.bind(("0.0.0.0", testPort))
    server.listen(10)
except OSError:
    testKO("Binding error. Aborting.")
    exit(-1)

for test in range(1, 6):
    stringToSend = "IPS-Testing-Script-"*2*test

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
    except socket.timeout:
        testKO(f"Test string not received (length: {len(stringToSend)})")

    time.sleep(0.3)

# Scaricare (o copiare) l'IPS
# Inserire regola

# Avviare IPS
# Avviare server in ascolto
# Avviare client con echo "goodword" | nc -v -q 1 127.0.0.1 2222
# Verificare che il server abbia ricevuto la stringa

# Avviare client con echo "badword" | nc -v -q 1 127.0.0.1 2222
# Verificare che il server non abbia ricevuto la stringa

# Summary results
totalTests = passedTests + failedTests
resultColor = red + "⚠️  "
if passedTests == totalTests:
    resultColor = lightGreen
resultString = f"Passed Tests: {resultColor}{passedTests} of {totalTests}"
print(f"{lightCyan}{resultString}{noColor}")
