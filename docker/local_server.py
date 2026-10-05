"""Adaptador HTTP local para la Lambda API, sin API Gateway ni Cognito real."""

import os
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Any
from urllib.parse import parse_qs, urlparse

import boto3
from api.app import handler  # type: ignore[import-not-found]
from botocore.exceptions import ClientError

TABLE_NAME = os.environ.get("TABLE_NAME", "brock-local")
ENDPOINT = os.environ.get("AWS_ENDPOINT_URL", "http://127.0.0.1:8000")


def dynamo() -> Any:
    return boto3.resource("dynamodb", endpoint_url=ENDPOINT, region_name="us-east-1")


def preparar_tabla() -> None:
    cliente = boto3.client("dynamodb", endpoint_url=ENDPOINT, region_name="us-east-1")
    try:
        cliente.describe_table(TableName=TABLE_NAME)
        if os.environ.get("LOCAL_RESET_TABLE") != "true":
            return
        cliente.delete_table(TableName=TABLE_NAME)
        waiter = cliente.get_waiter("table_not_exists")
        waiter.wait(TableName=TABLE_NAME)
    except cliente.exceptions.ResourceNotFoundException:
        pass
    cliente.create_table(
        TableName=TABLE_NAME,
        BillingMode="PAY_PER_REQUEST",
        KeySchema=[{"AttributeName": "PK", "KeyType": "HASH"},
                   {"AttributeName": "SK", "KeyType": "RANGE"}],
        AttributeDefinitions=[{"AttributeName": "PK", "AttributeType": "S"},
                              {"AttributeName": "SK", "AttributeType": "S"}],
    )


class Handler(BaseHTTPRequestHandler):
    server_version = "BrockLocal/1.0"

    def do_OPTIONS(self) -> None:
        self.send_response(204)
        self.end_headers()

    def do_GET(self) -> None:
        self.dispatch()

    def do_POST(self) -> None:
        self.dispatch()

    def do_PUT(self) -> None:
        self.dispatch()

    def do_PATCH(self) -> None:
        self.dispatch()

    def do_DELETE(self) -> None:
        self.dispatch()

    def dispatch(self) -> None:
        parsed = urlparse(self.path)
        length = int(self.headers.get("content-length", "0"))
        body = self.rfile.read(length).decode("utf-8") if length else None
        query: dict[str, str] | None = None
        if parsed.query:
            query = {key: values[-1] for key, values in parse_qs(parsed.query).items()}
        sub = self.headers.get("X-Local-User-Sub", "local-user")
        evento = {
            "version": "2.0", "rawPath": parsed.path, "body": body,
            "queryStringParameters": query,
            "requestContext": {"requestId": f"local-{time.time_ns()}", "stage": "$default",
                "http": {"method": self.command, "path": parsed.path},
                "authorizer": {"jwt": {"claims": {"sub": sub}}}},
        }
        resultado = handler(evento, None)
        payload = resultado.get("body", "")
        self.send_response(int(resultado.get("statusCode", 500)))
        for clave, valor in (resultado.get("headers") or {}).items():
            self.send_header(clave, str(valor))
        self.end_headers()
        if payload:
            self.wfile.write(payload.encode("utf-8"))

    def log_message(self, formato: str, *args: object) -> None:
        print(f"[http] {formato % args}", flush=True)


def main() -> None:
    while True:
        try:
            preparar_tabla()
            break
        except ClientError as exc:
            print(f"Esperando DynamoDB Local: {exc}", flush=True)
            time.sleep(1)
    puerto = int(os.environ.get("LOCAL_PORT", "3000"))
    print(f"Brock local escuchando en http://0.0.0.0:{puerto}", flush=True)
    ThreadingHTTPServer(("0.0.0.0", puerto), Handler).serve_forever()


if __name__ == "__main__":
    main()
