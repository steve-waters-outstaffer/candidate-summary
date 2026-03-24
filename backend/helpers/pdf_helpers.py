# helpers/pdf_helpers.py
# Generates branded Outstaffer PDFs from AI-generated HTML summaries.
# Uses WeasyPrint for full CSS support. Logo is base64-embedded (no file path deps in Cloud Run).

import io
import structlog
from weasyprint import HTML

log = structlog.get_logger()

# ---------------------------------------------------------------------------
# Outstaffer logo - base64-embedded SVG, no external file dependency
# ---------------------------------------------------------------------------
_LOGO_B64 = (
    "PD94bWwgdmVyc2lvbj0iMS4wIiBlbmNvZGluZz0idXRmLTgiPz4NCjwhLS0gR2VuZXJhdG9yOiBBZG9i"
    "ZSBJbGx1c3RyYXRvciAyMy4wLjYsIFNWRyBFeHBvcnQgUGx1Zy1JbiAuIFNWRyBWZXJzaW9uOiA2LjAw"
    "IEJ1aWxkIDApICAtLT4NCjwhRE9DVFlQRSBzdmcgUFVCTElDICItLy9XM0MvL0RURCBTVkcgMS4xLy9F"
    "TiIgImh0dHA6Ly93d3cudzMub3JnL0dyYXBoaWNzL1NWRy8xLjEvRFREL3N2ZzExLmR0ZCIgWw0KCTwh"
    "RU5USVRZIG5zX2V4dGVuZCAiaHR0cDovL25zLmFkb2JlLmNvbS9FeHRlbnNpYmlsaXR5LzEuMC8iPg0K"
    "CTwhRU5USVRZIG5zX2FpICJodHRwOi8vbnMuYWRvYmUuY29tL0Fkb2JlSWxsdXN0cmF0b3IvMTAuMC8i"
    "Pg0KCTwhRU5USVRZIG5zX2dyYXBocyAiaHR0cDovL25zLmFkb2JlLmNvbS9HcmFwaHMvMS4wLyI+DQoJ"
    "PCFFTlRJVFkgbnNfdmFycyAiaHR0cDovL25zLmFkb2JlLmNvbS9WYXJpYWJsZXMvMS4wLyI+DQoJPCFF"
    "TlRJVFkgbnNfaW1yZXAgImh0dHA6Ly9ucy5hZG9iZS5jb20vSW1hZ2VSZXBsYWNlbWVudC8xLjAvIj4N"
    "Cgk8IUVOVElUWSBuc19zZncgImh0dHA6Ly9ucy5hZG9iZS5jb20vU2F2ZUZvcldlYi8xLjAvIj4NCgk8"
    "IUVOVElUWSBuc19jdXN0b20gImh0dHA6Ly9ucy5hZG9iZS5jb20vR2VuZXJpY0N1c3RvbU5hbWVzcGFj"
    "ZS8xLjAvIj4NCgk8IUVOVElUWSBuc19hZG9iZV94cGF0aCAiaHR0cDovL25zLmFkb2JlLmNvbS9YUGF0"
    "aC8xLjAvIj4NCl0+DQo8c3ZnIHZlcnNpb249IjEuMSIgaWQ9IkxheWVyXzEiIHhtbG5zOng9IiZuc19l"
    "eHRlbmQ7IiB4bWxuczppPSImbnNfYWk7IiB4bWxuczpncmFwaD0iJm5zX2dyYXBoczsiDQoJIHhtbG5z"
    "PSJodHRwOi8vd3d3LnczLm9yZy8yMDAwL3N2ZyIgeG1sbnM6eGxpbms9Imh0dHA6Ly93d3cudzMub3Jn"
    "LzE5OTkveGxpbmsiIHg9IjBweCIgeT0iMHB4Ig0KCSB2aWV3Qm94PSIwIDAgNDIzLjE0NzQzMDQgODAu"
    "NDQ2NDcyMiIgc3R5bGU9ImVuYWJsZS1iYWNrZ3JvdW5kOm5ldyAwIDAgNDIzLjE0NzQzMDQgODAuNDQ2"
    "NDcyMjsiIHhtbDpzcGFjZT0icHJlc2VydmUiPg0KPHN0eWxlIHR5cGU9InRleHQvY3NzIj4NCgkuc3Qw"
    "e2ZpbGw6IzFBMzU2MTt9DQoJLnN0MXtmaWxsOiMwMEFFRDg7fQ0KPC9zdHlsZT4NCjxnIGlkPSJYTUxJ"
    "RF81MV8iPg0KCTxnIGlkPSJYTUxJRF8xMzdfIj4NCgkJPHBhdGggaWQ9IlhNTElEXzE1NV8iIGNsYXNz"
    "PSJzdDAiIGQ9Ik03Ny4zMTQzNzY4LDI4LjAxMDI3NjhjMC4xNDUwMzQ4LTEuMDU4MjY5NSwwLjIyNzc1"
    "MjctMi4xMzUxMDUxLDAuMjI3NzUyNy0zLjIzMDk3NjFjMC0yLjUwNDM0MTEtMC4zOTQzNzg3LTQuOTIw"
    "Mzg3My0xLjEyMTAwOTgtNy4xOTkwNjYyYy01LjUzNzk3MTUsMTcuMDAzMTI0Mi0xOC4xMDQzMDkxLDE1"
    "Ljc0MzY1NjItMTguMTA0MzA5MSwxNS43NDM2NTYybC0xLjA2ODA3NzEsMTIuMzg5NjQ4NEM3NS40MDU5"
    "ODMsNTEuOTA4MzYzMyw3NS40MDU5ODMsNjQuMDg0NDA0LDc1LjQwNTk4Myw2NC4wODQ0MDRjLTE0LjA5"
    "ODU3MTgtMTcuOTQzNjM0LTI2LjQ4ODIyMDItNy4yNjI5MDEzLTI2LjQ4ODIyMDItNy4yNjI5MDEzYy0z"
    "LjcwNjkxNjgsNC4yMzY0NjU1LTguMTQ4NzU3OSw3LjczMTE3MDctMTAuOTkzMzg1Myw5Ljc3ODgxNjJs"
    "MzguNTQ5Njc1LTAuMTY2MTUzYzE3LjUxNjQwMzItMS45MjI1Mzg4LDE3LjUxNjQwMzItMTYuODc1NTY0"
    "NiwxNy41MTY0MDMyLTE2Ljg3NTU2NDZDOTQuOTc4MTExMywzMi42MDM4NzQyLDgyLjkwNzc5MTEsMjgu"
    "ODQ0Mzk0Nyw3Ny4zMTQzNzY4LDI4LjAxMDI3Njh6Ii8+DQoJCTxwYXRoIGlkPSJYTUxJRF8xNDdfIiBj"
    "bGFzcz0ic3QxIiBkPSJNNDQuMTExNDM0OSwzMC44NjczMjFjLTEzLjEzNzMwODEtMi43NzY5OTI4LTE4"
    "LjI2NDA1OTEsNS44NzQ0MDExLTE4LjI2NDA1OTEsNS44NzQ0MDExbDUuMDE5OTQzMiwyLjY3MDE4MTNs"
    "LTQuMzc5MTAwOCw5LjI5MjI0NGwtMTIuNTMyMDc3OC02Ljk3ODA5Nmw0LjY5OTUyMzktOC45NzE4MTds"
    "Ni4yNjYxNzA1LDMuMjc1MDc3OGMyLjMxOTU5NTMtNy4wODA0NjcyLDguNTE1NjA0LTEwLjg1MzU4NDMs"
    "MTUuNjU2OTUzOC0xMS42Njg1Mjk1YzcuNDczNDY1LTAuODUyODQ0MiwxNC43NzM0NDUxLDMuNjk3NjEy"
    "OCwyMi4wMjMyMzE1LDIuMjg1NzM2MWM1LjY4NDAzNjMtMS4xMDY5NTI3LDEwLjI0MDkzNjMtNS42MDM3"
    "MjE2LDEzLjQyMzA1NzYtMTAuMjA2NTM1M0M3Mi40MjM0NjE5LDYuODU4MjAwMSw2Mi43OTYzMDI4LDAs"
    "NTEuNDgxMTQwMSwwQzM5LjQ5NTUwNjMsMCwyOS40MDY0ODg0LDcuNjk1ODY1NiwyNi4zNjQ0MDg1LDE4"
    "LjE3MjExMTVjLTAuMjA4MDM0NS0wLjAwNDY5NTktMC40MTQ2MDgtMC4wMTQ4NjU5LTAuNjIzODQwMy0w"
    "LjAxNDg2NTlDMTEuNTI0NDUwMywxOC4xNTcyNDU2LDAsMjkuMDEyMjE4NSwwLDQyLjQwMjUxMTZDMCw1"
    "NC40NjY0MjMsOS4zNTU4NjM2LDY0LjQ2ODI5MjIsMjEuNjA1MzI5NSw2Ni4zMzIyMDY3QzQ5LjM0MjQ5"
    "MTEsNjIuNTgzNjI1OCw0NC4xMTE0MzQ5LDMwLjg2NzMyMSw0NC4xMTE0MzQ5LDMwLjg2NzMyMXoiLz4N"
    "CgkJPHJlY3QgaWQ9IlhNTElEXzE0NF8iIHg9Ijc0LjU1NDAzOSIgeT0iNC4yNzczMjg1IiBjbGFzcz0i"
    "c3QwIiB3aWR0aD0iNi40MDM0MDQyIiBoZWlnaHQ9IjYuNDAzNDA0MiIvPg0KCQk8cmVjdCBpZD0iWE1M"
    "SUQiIHg9Ijg0LjM4MDMxNzciIHk9IjEuNzE2NDcyNiIgY2xhc3M9InN0MCIgd2lkdGg9IjQuMDUxMTI0"
    "NiIgaGVpZ2h0PSI0LjA1MTEyNDYiLz4NCgkJPHJlY3QgaWQ9IlhNTElEXzEzOF8iIHg9Ijg0LjM4MDMx"
    "NzciIHk9IjEwLjc1NDQ1NTYiIGNsYXNzPSJzdDEiIHdpZHRoPSI0LjA1MTEyNDYiIGhlaWdodD0iNC4w"
    "NTExMjQ2Ii8+DQoJPC9nPg0KCTxnIGlkPSJYTUxJRF81NDlfIj4NCgkJPHBhdGggY2xhc3M9InN0MCIg"
    "ZD0iTTEwMS4yMjksMjQuNjR2LTAuMDg3YzAtOC42NjksNi44MzktMTUuNzcsMTYuMjQ5LTE1Ljc3czE2"
    "LjE2Miw3LjAxNCwxNi4xNjIsMTUuNjgzdjAuMDg3YzAsOC42NjktNi44MzksMTUuNzctMTYuMjQ5LDE1"
    "Ljc3UzEwMS4yMjksMzMuMzA5LDEwMS4yMjksMjQuNjR6IE0xMjYuNjI2LDI0LjY0di0wLjA4N2MwLTUu"
    "MjI4LTMuODMzLTkuNTg0LTkuMjM1LTkuNTg0cy05LjE0OCw0LjI3LTkuMTQ4LDkuNDk3djAuMDg3YzAs"
    "NS4yMjgsMy44MzMsOS41ODQsOS4yMzUsOS41ODRTMTIwLjYyNiwyOS44NjgsMTI2LjYyNiwyNC42NHoN"
    "CgkJTTEzOC43NDEsMzEuNTU3VjE2LjQ0aDYuNjIydjEzLjAyNWMwLDMuMTM3LDEuNDgxLDQuNzQ5LDQu"
    "MDA4LDQuNzQ5czQuMTM5LTEuNjEyLDQuMTM5LTQuNzQ5VjE2LjQ0aDYuNjIydjIzLjM1aC02LjYyMnYt"
    "My4zMTFjLTEuNTI1LDEuOTYtMy40ODUsMy43NDctNi44MzksMy43NDdDMTQxLjY2LDQwLjIyNiwxMzgu"
    "NzQxLDM2LjkxNSwxMzguNzQxLDMxLjU1N3oNCgkJTTE2Ny4xNDYsMzMuMTY5VjIyLjEwM2gtMi43ODhW"
    "MTYuNDRoMi43ODh2LTUuOTY4aDYuNjIydjUuOTY4aDUuNDg5djUuNjYzaC01LjQ4OXY5Ljk3NmMwLDEu"
    "NTI1LDAuNjUzLDIuMjY2LDIuMTM0LDIuMjY2YzEuMjIsMCwyLjMwOS0wLjMwNSwzLjI2OC0wLjgyOHY1"
    "LjMxNWMtMS4zOTQsMC44MjgtMy4wMDYsMS4zNS01LjIyOCwxLjM1QzE2OS44OTEsNDAuMTgsMTY3LjE0"
    "NiwzOC41NjksMTY3LjE0NiwzMy4xNjl6DQoJCU0xODIuMzA4LDM2LjY5N2wyLjgzMi00LjM1NmMyLjUy"
    "NywxLjgzLDUuMTg0LDIuNzg4LDcuMzYyLDIuNzg4YzEuOTE3LDAsMi43ODgtMC42OTcsMi43ODgtMS43"
    "NDN2LTAuMDg3YzAtMS40MzgtMi4yNjUtMS45MTctNC44MzUtMi43MDFjLTMuMjY4LTAuOTU5LTYuOTcx"
    "LTIuNDgzLTYuOTcxLTcuMDE0di0wLjA4N2MwLTQuNzQ5LDMuODMzLTcuNDA2LDguNTM4LTcuNDA2YzIu"
    "OTYyLDAsNi4xODcsMS4wMDIsOC43MTMsMi43MDFsLTIuNTI2LDQuNTc0Yy0yLjMwOS0xLjM1LTQuNjE4"
    "LTIuMTc4LTYuMzE3LTIuMTc4Yy0xLjYxMiwwLTIuNDM5LDAuNjk3LTIuNDM5LDEuNjEydjAuMDg3YzAs"
    "MS4zMDcsMi4yMjIsMS45MTcsNC43NDgsMi43ODhjMy4yNjgsMS4wOSw3LjA1OCwyLjY1Nyw3LjA1OCw2"
    "LjkyN3YwLjA4N2MwLDUuMTg0LTMuODc3LDcuNTM3LTguOTMxLDcuNTM3QzE4OS4wNjEsNDAuMjI2LDE4"
    "NS40MDEsMzkuMTM3LDE4Mi4zMDgsMzYuNjk3eg0KCQlNMjA2LjY2MiwzMy4xNjlWMjIuMTAzaC0yLjc4"
    "OFYxNi40NGgyLjc4OHYtNS45NjhoNi42MjJ2NS45NjhoNS40ODl2NS42NjNoLTUuNDg5djkuOTc2YzAs"
    "MS41MjUsMC42NTMsMi4yNjYsMi4xMzQsMi4yNjZjMS4yMiwwLDIuMzA5LTAuMzA1LDMuMjY4LTAuODI4"
    "djUuMzE1Yy0xLjM5NCwwLjgyOC0zLjAwNiwxLjM1LTUuMjI4LDEuMzVDMjA5LjQwNyw0MC4xOCwyMDYu"
    "NjYyLDM4LjU2OSwyMDYuNjYyLDMzLjE2OXoNCgkJTTIyMi4yNiwzMy4wODJ2LTAuMDg3YzAtNS4wOTcs"
    "My44NzctNy40NSw5LjQxLTcuNDVjMi4zNTMsMCw0LjA1MSwwLjM5Miw1LjcwNywwLjk1OHYtMC4zOTJj"
    "MC0yLjc0NC0xLjY5OS00LjI2OS01LjAxLTQuMjY5Yy0yLjUyNywwLTQuMzEzLDAuNDc5LTYuNDQ4LDEu"
    "MjYzbC0xLjY1NS01LjA1M2MyLjU3LTEuMTMzLDUuMDk3LTEuODc0LDkuMDYxLTEuODc0YzMuNjE2LDAs"
    "Ni4yMywwLjk1OSw3Ljg4NSwyLjYxNGMxLjc0MywxLjc0MiwyLjUyNyw0LjMxMywyLjUyNyw3LjQ0OXYx"
    "My41NDhoLTYuNDA0di0yLjUyN2MtMS42MTIsMS43ODYtMy44MzQsMi45NjItNy4wNTgsMi45NjJDMjI1"
    "Ljg3NSw0MC4yMjYsMjIyLjI2LDM3LjcsMjIyLjI2LDMzLjA4MnogTTIzNy40NjMsMzEuNTU3di0xLjE3"
    "NmMtMS4xMzItMC41MjMtMi42MTQtMC44NzItNC4yMjYtMC44NzJjLTIuODMxLDAtNC41NzQsMS4xMzMt"
    "NC41NzQsMy4yMjR2MC4wODdjMCwxLjc4NiwxLjQ4MSwyLjgzMiwzLjYxNiwyLjgzMkMyMzUuMzczLDM1"
    "LjY1MiwyMzcuNDYzLDMzLjk1MywyMzcuNDYzLDMxLjU1N3oNCgkJTTI1MC41NzksMjIuMTAzaC0yLjc0"
    "NXYtNS40NDVoMi43NDV2LTEuNDgxYzAtMi41NywwLjY1My00LjQ0MywxLjg3My01LjY2M3MzLjAwNi0x"
    "LjgzLDUuMzU4LTEuODNjMi4wOTEsMCwzLjQ4NSwwLjI2MSw0LjcwNSwwLjY1M3Y1LjQ4OWMtMC45NTgt"
    "MC4zNDktMS44NzMtMC41NjYtMy4wMDYtMC41NjZjLTEuNTI0LDAtMi4zOTYsMC43ODQtMi4zOTYsMi41"
    "MjZ2MC45MTVoNS4zNTh2NS40MDJoLTUuMjcxdjE3LjY4N2gtNi42MjJWMjIuMTAzeg0KCQlNMjY3LjIy"
    "MSwyMi4xMDNoLTIuNzQ1di01LjQ0NWgyLjc0NXYtMS40ODFjMC0yLjU3LDAuNjUzLTQuNDQzLDEuODcz"
    "LTUuNjYzczMuMDA2LTEuODMsNS4zNTgtMS44M2MyLjA5MSwwLDMuNDg1LDAuMjYxLDQuNzA1LDAuNjUz"
    "djUuNDg5Yy0wLjk1OC0wLjM0OS0xLjg3My0wLjU2Ni0zLjAwNi0wLjU2NmMtMS41MjQsMC0yLjM5Niww"
    "Ljc4NC0yLjM5NiwyLjUyNnYwLjkxNWg1LjM1OHY1LjQwMmgtNS4yNzF2MTcuNjg3aC02LjYyMlYyMi4x"
    "MDN6DQoJCU0yODEuMTYzLDI4LjI0NnYtMC4wODdjMC02LjY2NSw0Ljc0OC0xMi4xNTQsMTEuNTQ0LTEy"
    "LjE1NGM3Ljc5OCwwLDExLjM3LDYuMDU1LDExLjM3LDEyLjY3N2MwLDAuNTIzLTAuMDQzLDEuMTMzLTAu"
    "MDg3LDEuNzQzaC0xNi4yNWMwLjY1MywzLjAwNiwyLjc0NCw0LjU3NCw1LjcwNyw0LjU3NGMyLjIyMiww"
    "LDMuODMzLTAuNjk3LDUuNjYzLTIuMzk2bDMuNzksMy4zNTVjLTIuMTc4LDIuNzAxLTUuMzE0LDQuMzU2"
    "LTkuNTQxLDQuMzU2QzI4Ni4zNDcsMzkuMzM0LDI4MS4xNjMsMzQuNDExLDI4MS4xNjMsMjguMjQ2ek0y"
    "OTcuNjMsMjYuMjg2Yy0wLjM5Mi0yLjk2Mi0yLjEzNS00Ljk2Ni00LjkyMy00Ljk2NmMtMi43NDQsMC00"
    "LjUzMSwxLjk2LTUuMDUzLDQuOTY2SDI5Ny42M3oNCgkJTTMwOS4wMDIsMTYuNDRoNi42MjJ2NC43MDVj"
    "MS4zNS0zLjIyNCwzLjUyOS01LjMxNCw3LjQ1LTUuMTR2Ni45MjZoLTAuMzQ5Yy00LjQsMC03LjEwMSwy"
    "LjY1Ny03LjEwMSw4LjIzNHY4LjYyNWgtNi42MjJWMTYuNDR6DQoJCU0zMjcuODI0LDM2LjA4N2gyLjg3"
    "NXYzLjcwM2gtMi44NzVWMzYuMDg3eg0KCQlNMzM1LjkyOCwyOC43N3YtMC4wODdjMC02LjIzLDQuOTY2"
    "LTExLjYzMSwxMS4zMjctMTEuNjMxYzQuMTgyLDAsNi43OTYsMS45MTcsOC44ODcsNC4wOTVsLTEuNTI0"
    "LDEuNTY4Yy0xLjkxNy0xLjk2LTQuMDk1LTMuNjU5LTcuNDA2LTMuNjU5Yy01LjA1MywwLTguOTc0LDQu"
    "MjI2LTguOTc0LDkuNTQxdjAuMDg3YzAsNS4zNTgsNC4wNTIsOS42MjgsOS4xNDgsOS42MjhjMy4xMzcs"
    "MCw1LjU3Ni0xLjYxMiw3LjQ1LTMuNzAzbDEuNDgxLDEuMzA3Yy0yLjI2NSwyLjU3LTQuOTY2LDQuNC05"
    "LjA2MSw0LjRDMzQwLjg1LDM5LjMzNCwzMzUuOTI4LDM0Ljk5OSwzMzUuOTI4LDI4Ljc3eg0KCQlNMzYw"
    "LjE1MiwyOC43N3YtMC4wODdjMC02LjIzLDQuODM1LTExLjYzMSwxMS40NTctMTEuNjMxYzYuNTc4LDAs"
    "MTEuMzcsNS4zMTQsMTEuMzcsOS41NDR2MC4wODdjMCw2LjIzLTQuODM1LDExLjYzMS0xMS40NTcsMTEu"
    "NjMxQzM2NC45NDQsMzkuMzM0LDM2MC4xNTIsMzQuOTk5LDM2MC4xNTIsMjguNzd6IE0zODAuNjcsMjgu"
    "Nzd2LTAuMDg3YzAtNS4zNTgtNC4wMDgtOS42MjctOS4xNDgtOS42MjdjLTUuMjcxLDAtOS4wNjIsNC4z"
    "MTMtOS4wNjIsOS41NDF2MC4wODdjMCw1LjM1OCw0LjAwOCw5LjYyOCw5LjE0OCw5LjYyOEMzNzYuODgx"
    "LDM4LjMxMiwzODAuNjcsMzQuMDAxLDM4MC42NywyOC43N3oNCgkJTTM4OS41NiwxNy41NzJoMi4xMzV2"
    "My45NjRjMS40MzgtMi4zMDksMy40NDEtNC40ODcsNy40MDYtNC40ODdjMy44NzcsMCw2LjI3MywyLjIy"
    "Miw3LjQ5Myw0Ljc5MmMxLjQzOC0yLjQ4MywzLjgzMy00Ljc5Miw4LjAxNi00Ljc5MmM1LjI3MSwwLDgu"
    "NTM5LDMuNzAyLDguNTM5LDkuMjc5djEzLjQ2MWgtMi4xMzV2LTEzLjJjMC00Ljc5Mi0yLjQ4My03LjU4"
    "LTYuNTc4LTcuNThjLTMuNzQ3LDAtNy4wMTQsMi44NzUtNy4wMTQsNy44NDF2MTIuOTM5aC0yLjEzNVYy"
    "Ni40NmMwLTQuNjE4LTIuNTI2LTcuNDQ5LTYuNDkxLTcuNDQ5cy03LjEwMSwzLjQ4NS03LjEwMSw3Ljk3"
    "MnYxMi44MDhoLTIuMTM1VjE3LjU3MnoiLz4NCgk8L2c+DQo8L2c+DQo8L3N2Zz4="
)
LOGO_SRC = f"data:image/svg+xml;base64,{_LOGO_B64}"

# ---------------------------------------------------------------------------
# Brand colours
# ---------------------------------------------------------------------------
NAVY   = "#1B3360"
LIGHT  = "#EEF3FF"
BORDER = "#C8D5EE"
DARK   = "#1A1A2E"
MID    = "#4A5568"
WHITE  = "#FFFFFF"

# ---------------------------------------------------------------------------
# CSS - WeasyPrint supports position:fixed, backgrounds, modern layout
# ---------------------------------------------------------------------------
PDF_CSS = f"""
@page {{
    size: A4;
    margin: 76pt 24pt 36pt 24pt;
}}

body {{
    font-family: Arial, Helvetica, sans-serif;
    font-size: 9.5pt;
    color: {DARK};
    margin: 0;
    padding: 0;
}}

/* ---- Header fixed to top of every page ---- */
.pdf-header {{
    position: fixed;
    top: -76pt;
    left: -24pt;
    right: -24pt;
    height: 56pt;
    background-color: {WHITE};
    padding: 8pt 20pt;
    display: flex;
    align-items: center;
    justify-content: space-between;
}}

.pdf-header img {{
    height: 30pt;
    width: auto;
}}

.pdf-header-right {{
    font-size: 7pt;
    color: {MID};
    letter-spacing: 0.5pt;
    text-transform: uppercase;
    text-align: right;
}}

/* ---- Footer fixed to bottom of every page ---- */
.pdf-footer {{
    position: fixed;
    bottom: -36pt;
    left: -24pt;
    right: -24pt;
    height: 26pt;
    background-color: {NAVY};
    padding: 5pt 20pt;
    display: flex;
    align-items: center;
    justify-content: space-between;
}}

.pdf-footer-text {{
    font-size: 7pt;
    color: #A8C4F5;
}}

/* ---- Navy accent line below header ---- */
.pdf-header-accent {{
    position: fixed;
    top: -20pt;
    left: -24pt;
    right: -24pt;
    height: 3pt;
    background-color: {NAVY};
}}

/* ---- Body content ---- */
h1 {{
    font-size: 14pt;
    color: {NAVY};
    margin: 0 0 4pt 0;
}}

h2 {{
    font-size: 10.5pt;
    color: {NAVY};
    border-bottom: 1pt solid {BORDER};
    padding-bottom: 2pt;
    margin: 10pt 0 4pt 0;
}}

h3 {{
    font-size: 9.5pt;
    color: {NAVY};
    margin: 6pt 0 2pt 0;
}}

p {{
    margin: 2pt 0 5pt 0;
    line-height: 1.45;
}}

ul, ol {{
    margin: 2pt 0 5pt 14pt;
    padding: 0;
}}

li {{
    margin-bottom: 2pt;
    line-height: 1.4;
}}

.candidate-block {{
    background-color: {LIGHT};
    border-left: 4pt solid {NAVY};
    padding: 8pt 12pt;
    margin-bottom: 10pt;
}}

.candidate-block h1 {{
    font-size: 15pt;
    margin-bottom: 3pt;
}}

.candidate-block p {{
    margin: 1pt 0;
    color: {MID};
    font-size: 8.5pt;
}}
/* ---- kv-table (candidate details header block) ---- */
table.kv-table {{
    width: 100%;
    border-collapse: collapse;
    border: 1pt solid {BORDER};
    margin-bottom: 10pt;
}}

table.kv-table tr {{
    border-bottom: 1pt solid {BORDER};
}}

table.kv-table tr:last-child {{
    border-bottom: none;
}}

table.kv-table td {{
    padding: 4pt 8pt;
    font-size: 9pt;
    vertical-align: top;
}}

table.kv-table td.key {{
    width: 30%;
    font-weight: bold;
    background-color: {NAVY};
    color: {WHITE};
    border-right: 1pt solid {BORDER};
}}
"""

# ---------------------------------------------------------------------------
# HTML wrapper template
# ---------------------------------------------------------------------------
PDF_TEMPLATE = """<!DOCTYPE html>
<html>
<head>
<meta charset="UTF-8"/>
<style>
{css}
</style>
</head>
<body>

<div class="pdf-header">
    <img src="{logo}" alt="Outstaffer"/>
    <div class="pdf-header-right">Global Talent &nbsp;&#183;&nbsp; Candidate Profile</div>
</div>
<div class="pdf-header-accent"></div>

<div class="pdf-footer">
    <span class="pdf-footer-text">Confidential &#8212; Prepared by Outstaffer &nbsp;&#183;&nbsp; outstaffer.com</span>
    <span class="pdf-footer-text">This profile is provided for evaluation purposes only</span>
</div>

{content}

</body>
</html>"""


def _wrap_html_for_pdf(html_content: str) -> str:
    """Wrap raw AI summary HTML in the branded Outstaffer PDF template."""
    return PDF_TEMPLATE.format(css=PDF_CSS, logo=LOGO_SRC, content=html_content)


def generate_pdf_from_html(html_content: str, candidate_name: str, job_name: str) -> tuple:
    """
    Generate a branded Outstaffer PDF from AI-generated HTML content.

    Args:
        html_content (str): Raw HTML summary from the AI model
        candidate_name (str): Used for the output filename
        job_name (str): Used for the output filename

    Returns:
        tuple: (pdf_bytes, filename) or (None, None) on failure
    """
    try:
        safe_candidate = candidate_name.replace(" ", "_").replace("/", "_")
        safe_job       = job_name.replace(" ", "_").replace("/", "_")
        filename       = f"{safe_candidate}-{safe_job}.pdf" if safe_job else f"{safe_candidate}.pdf"

        wrapped_html = _wrap_html_for_pdf(html_content)
        pdf_bytes    = HTML(string=wrapped_html).write_pdf()

        if not pdf_bytes:
            log.error("pdf.generation.failed", error="WeasyPrint returned empty bytes")
            return None, None

        log.info("pdf.generated", filename=filename, size=len(pdf_bytes))
        return pdf_bytes, filename

    except Exception as e:
        log.error("pdf.generation.failed", error=str(e))
        return None, None
