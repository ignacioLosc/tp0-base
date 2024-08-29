import sys

def generateServer(f):
    f.write("name: tp0\n")
    f.write("services:\n")
    f.write("  server:\n")
    f.write("    container_name: server\n")
    f.write("    image: server:latest\n")
    f.write("    entrypoint: python3 /main.py\n")
    f.write("    volumes:\n")
    f.write("      - ${PWD}/server/config.ini:/config.ini\n")
    f.write("    environment:\n")
    f.write("      - PYTHONUNBUFFERED=1\n")
    f.write("      - LOGGING_LEVEL=DEBUG\n")
    f.write("    networks:\n")
    f.write("      - testing_net\n\n")

def generateClient(f, id):
    f.write("  client" + str(id) + ":\n")
    f.write("    container_name: client" + str(id) + "\n")
    f.write("    image: client:latest\n")
    f.write("    entrypoint: /client\n")
    f.write("    volumes:\n")
    f.write("      - ${PWD}/client/config.yaml:/config.yaml\n")
    f.write("    environment:\n")
    f.write("      - CLI_ID=" + str(id) + "\n")
    f.write("      - CLI_LOG_LEVEL=DEBUG\n")
    f.write("    networks:\n")
    f.write("      - testing_net\n")
    f.write("    depends_on:\n")
    f.write("      - server\n\n")

def generateNetwork(f):
    f.write("networks:\n")
    f.write("  testing_net:\n")
    f.write("    ipam:\n")
    f.write("      driver: default\n")
    f.write("      config:\n")
    f.write("        - subnet: 172.25.125.0/24\n")

def generateDockerCompose(file_name, client_count):
    f = open(file_name, "w")
    generateServer(f)
    for id in range(1, int(client_count) + 1):
        generateClient(f, id)
    generateNetwork(f)
    f.close()

if __name__ == '__main__':
    generateDockerCompose(sys.argv[1], sys.argv[2])
