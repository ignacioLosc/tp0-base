# TP0: Docker + Comunicaciones + Concurrencia

En el presente repositorio se presenta la solucion a los ejercicios planteados por el trabajo practico, en donde cada resolucion de un ejercicio se ubica en una rama distinta. Para dicha resolucion se plantea la arquitectura cliente-servidor que se ejecutaran como dos procesos distintos conectados a traves de sockets y un protocolo de comunicacion.

En cada ejercicio puede ejecutarse el comando `make docker-compose-up` para iniciar los procesos cliente y servidor y `make docker-compose-logs` para observar los logs.

## Servidor
El servidor esta diseñado en Python segun el modelo base provisto por la catedra. Ademas posee la capacidad de soportar a varios clientes de forma concurrente debido al uso de threads y la sincronizacion para mantener siempre un estado valido al modificar recursos compartidos. El comportamiento es el descripto por la catedra, permitiendo recibir apuestas tanto individuales como en batch que contienen informacion sobre una persona y el numero asociado. Mientras el servidor se encuentra en ejecucion se pertisten las apuestas realizadas, de manera que se pueda proceder con el sorteo para determinar las personas ganadoras.
### Multithreading en Python
Si bien para la resolucion del trabajo se utilizo la api de threads provista por Python, es importante tener en cuenta las limitaciones del lenguaje en cuanto a la concurrencia con threads debido al mecanismo GIL (global interpreter lock). Para lograr paralelismo puro en Python es necesario utilizar procesos separados, dado que cada uno tendra su propio GIL.

## Cliente
El servidor esta diseñado en Go segun el modelo base provisto por la catedra. Recibe por variables de entorno la ubicacion del dataset a utilizar para realizar las apuestas, el id utilizar para diferenciarse de los demas clientes y el tamaño maximo de apuestas a realizar en batch (siendo 8kb una cota superior para el tamaño del paquete sin importar el tamaño del batch provisto por config). Una vez que realiza todas las apuestas, espera por la realizacion del sorteo y recibe del servidor todos los ganadores que haya habido correspondientes a su agencia (dada por el id).
## Protocolo
Para la comunicacion entre el cliente y el servidor es necesario que ambos comprendan el formato de la informacion que deben comunicarse. Para ello se definen varios elementos que componen al protocolo:

ACCION: Indica la accion a realizar por parte del cliente o del servidor. Las acciones posibles son:

- APUESTA: Accion que envia el cliente ara realizar una apuesta
- FINAPUESTA: Accion que envia el cliente para notificar el fin del envio de las apuestas del batch
- CONFIRMARAPUESTA: Accion que enviar el servidor para indicar la confirmacion de todas las apuestas de un batch
- GANADORES: Accion que envian el cliente y el servidor para pedir y para dar los ganadores por agencia

DELIMITADORES: Ayudan a la separacion de los distintos campos que componen un mensaje

Delimitador de mensajes: '\n'
   - Se utiliza para tener conocimiento del fin de un mensaje

Delimitador de comandos: ';'
   - Se utiliza para delimitar comandos dentro de un mensaje. Por ejemplo se pueden enviar varias apuestas dentro de un mensaje

Delimitador de campos: '|'
   - Se utiliza para poder separar los campos de un comando

Por ejemplo, para el realizar una apuesta se utilizaran los siguientes campos:

- ACCION (APUESTA)
- ID (ID de agencia)
- NOMBRE
- APELLIDO
- DOCUMENTO
- NACIMIENTO
- NUMERO

## Sincronizacion
### Mutex
En el presente trabajo se utiliza el mutex como herramienta de sincronizacion del uso de un recurso compartido entre varios threads, como puede ser la libreria apuestas provista por la catedra, cuyas funciones no son thread-safe y controlan el acceso a un recurso compartido.

Ejemplos de uso:

```
with self._lock:
            store_bets(bets)
```

```
with self._lock:
            list_of_bets = load_bets()
            for bet in list_of_bets:
                if bet.agency == int(agency) and has_won(bet):
                    winners_documents.append(bet.document)
```

### Barrera
La barrera es otra herramienta de sincronizacion que se utiliza para determinar el momento a realizar el sorteo, dado que es necesario que todas las cinco agencias hayan finalizado las apuestas para poder determinar ganadores. En consecuencia, las agencias que hayan terminado primero deberan esperar a las demas mediante una barrera, lo que permite ademas que la espera no sea con un mal uso de los recursos como busy-wait.
## Docker
Como parte del trabajo, se utiliza docker para la creacion de containers que aislen al entorno de ejecucion de los procesos cliente servidor del resto del sistema. Se utiliza un archivo docker compose, asi como un script generador del mismo, volumenes para la persistencia de la configuracion y variables de entorno para por ejemplo indicar el nivel del logger.