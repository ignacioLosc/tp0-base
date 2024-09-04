# Protocolo

El mensaje que envia el cliente tiene todos los campos requeridos separados por un caracter separador. Hay un caracter separador de mensajes para distinguir cuando termina un mensaje y comienza otro.

Caracter separador de campos: |
Caracter separador de mensajes: ;
Simbolo que indica fin de la request: \n

Campos que se van a enviar:
- ACCION
- ID
- NOMBRE
- APELLIDO
- DOCUMENTO
- NACIMIENTO
- NUMERO

ACCION puede ser: (cliente) APUESTA, (cliente) FINAPUESTAS, (servidor) CONFIRMARAPUESTA

Ejemplo:
ID1|NOMBRE1|APELLIDO1|DOCUMENTO1|NACIMIENTO1|NUMERO1;ID2|NOMBRE2|APELLIDO2|DOCUMENTO2|NACIMIENTO2|NUMERO2\n
