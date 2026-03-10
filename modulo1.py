
"""módulo simple de ejemplo.

Este módulo contiene una función `main()` que pide el nombre
del usuario por la entrada estándar y muestra un saludo.

Ejemplo de uso:
	$ python3 modulo1.py
	¿Cómo te llamas? (deja vacío para 'mundo'): Néstor
	¡Hola, Néstor!
"""

from typing import Optional


def main() -> None:
	"""Ejecuta el programa interactivo de saludo.

	Lee una línea desde la entrada estándar preguntando el nombre
	del usuario. Si la entrada está vacía, usa "mundo" por defecto.
	Imprime el saludo formateado.

	No devuelve nada.
	"""
	name: Optional[str] = input("¿Cómo te llamas? (deja vacío para 'mundo'): ").strip()
	if not name:
		name = "mundo"
	print(f"¡Hola, {name}!")


if __name__ == "__main__":
	main()

