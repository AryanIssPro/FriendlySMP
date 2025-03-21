import logging
import json
from jsonschema import validate
from jsonschema.exceptions import ValidationError
from playhouse.shortcuts import model_to_dict
from app.classes.models.server_permissions import EnumPermissionsServer
from app.classes.web.base_api_handler import BaseApiHandler

logger = logging.getLogger(__name__)

# TODO: modify monitoring
server_patch_schema = {
    "type": "object",
    "properties": {
        "server_name": {
            "type": "string",
            "minLength": 2,
            "pattern": r"^[^/\\\\#]*$",
            "error": "serverCreateName",
        },
        "backup_path": {
            "type": "string",
            "error": "typeString",
            "fill": True,
        },
        "executable": {
            "type": "string",
            "error": "typeString",
            "fill": True,
        },
        "log_path": {
            "type": "string",
            "minLength": 1,
            "error": "serverLogPath",
        },
        "execution_command": {
            "type": "string",
            "minLength": 1,
            "error": "serverExeCommand",
        },
        "java_selection": {
            "type": "string",
            "error": "typeString",
            "fill": True,
        },
        "auto_start": {
            "type": "boolean",
            "error": "typeBool",
            "fill": True,
        },
        "auto_start_delay": {
            "type": "integer",
            "minimum": 0,
            "error": "typeIntMinVal0",
            "fill": True,
        },
        "crash_detection": {
            "type": "boolean",
            "error": "typeBool",
            "fill": True,
        },
        "stop_command": {
            "type": "string",
            "error": "typeString",
            "fill": True,
        },
        "executable_update_url": {
            "type": "string",
            "error": "typeString",
            "fill": True,
        },
        "server_ip": {
            "type": "string",
            "minLength": 1,
            "error": "typeString",
            "fill": True,
        },
        "server_port": {
            "type": "integer",
            "error": "typeInt",
            "fill": True,
        },
        "shutdown_timeout": {
            "type": "integer",
            "minimum": 0,
            "error": "typeIntMinVal0",
            "fill": True,
        },
        "logs_delete_after": {
            "type": "integer",
            "minimum": 0,
            "error": "typeIntMinVal0",
            "fill": True,
        },
        "ignored_exits": {
            "type": "string",
            "error": "typeString",
            "fill": True,
        },
        "show_status": {
            "type": "boolean",
            "error": "typeBool",
            "fill": True,
        },
        "count_players": {
            "type": "boolean",
            "error": "typeBool",
            "fill": True,
        },
    },
    "additionalProperties": False,
    "minProperties": 1,
}
basic_server_patch_schema = {
    "type": "object",
    "properties": {
        "server_name": {
            "type": "string",
            "minLength": 1,
            "error": "serverCreateName",
            "fill": True,
        },
        "executable": {
            "type": "string",
            "error": "typeString",
            "fill": True,
        },
        "java_selection": {
            "type": "string",
            "error": "typeString",
            "fill": True,
        },
        "auto_start": {
            "type": "boolean",
            "error": "typeBool",
            "fill": True,
        },
        "auto_start_delay": {
            "type": "integer",
            "minimum": 0,
            "error": "typeIntMinVal0",
            "fill": True,
        },
        "crash_detection": {
            "type": "boolean",
            "error": "typeBool",
            "fill": True,
        },
        "stop_command": {
            "type": "string",
            "error": "typeString",
            "fill": True,
        },
        "shutdown_timeout": {
            "type": "integer",
            "error": "typeInteger",
            "fill": True,
        },
        "logs_delete_after": {
            "type": "integer",
            "minimum": 0,
            "error": "typeIntMinVal0",
            "fill": True,
        },
        "ignored_exits": {
            "type": "string",
            "error": "typeString",
            "fill": True,
        },
        "count_players": {
            "type": "boolean",
            "error": "typeBool",
            "fill": True,
        },
    },
    "additionalProperties": False,
    "minProperties": 1,
}


class ApiServersServerIndexHandler(BaseApiHandler):
    def get(self, server_id: str):
        auth_data = self.authenticate_user()
        if not auth_data:
            return

        if server_id not in [str(x["server_id"]) for x in auth_data[0]]:
            # if the user doesn't have access to the server, return an error
            return self.finish_json(
                400,
                {
                    "status": "error",
                    "error": "NOT_AUTHORIZED",
                    "error_data": self.helper.translation.translate(
                        "validators", "insufficientPerms", auth_data[4]["lang"]
                    ),
                },
            )

        server_obj = self.controller.servers.get_server_obj(server_id)
        server = model_to_dict(server_obj)

        # TODO: limit some columns for specific permissions?

        self.finish_json(200, {"status": "ok", "data": server})

    def patch(self, server_id: str):
        auth_data = self.authenticate_user()
        if not auth_data:
            return

        try:
            data = json.loads(self.request.body)
        except json.decoder.JSONDecodeError as e:
            return self.finish_json(
                400, {"status": "error", "error": "INVALID_JSON", "error_data": str(e)}
            )

        try:
            # prevent general users from becoming bad actors
            if auth_data[4]["superuser"]:
                validate(data, server_patch_schema)
            else:
                validate(data, basic_server_patch_schema)
        except ValidationError as why:
            offending_key = ""
            if why.schema.get("fill", None):
                offending_key = why.path[0] if why.path else None
            err = f"""{offending_key} {self.translator.translate(
                "validators",
                why.schema.get("error"),
                self.controller.users.get_user_lang_by_id(auth_data[4]["user_id"]),
            )} {why.schema.get("enum", "")}"""
            return self.finish_json(
                400,
                {
                    "status": "error",
                    "error": "INVALID_JSON_SCHEMA",
                    "error_data": f"{str(err)}",
                },
            )

        if server_id not in [str(x["server_id"]) for x in auth_data[0]]:
            # if the user doesn't have access to the server, return an error
            return self.finish_json(
                400,
                {
                    "status": "error",
                    "error": "NOT_AUTHORIZED",
                    "error_data": self.helper.translation.translate(
                        "validators", "insufficientPerms", auth_data[4]["lang"]
                    ),
                },
            )
        mask = self.controller.server_perms.get_lowest_api_perm_mask(
            self.controller.server_perms.get_user_permissions_mask(
                auth_data[4]["user_id"], server_id
            ),
            auth_data[5],
        )
        server_permissions = self.controller.server_perms.get_permissions(mask)
        if EnumPermissionsServer.CONFIG not in server_permissions:
            # if the user doesn't have Config permission, return an error
            return self.finish_json(
                400,
                {
                    "status": "error",
                    "error": "NOT_AUTHORIZED",
                    "error_data": self.helper.translation.translate(
                        "validators", "insufficientPerms", auth_data[4]["lang"]
                    ),
                },
            )

        server_obj = self.controller.servers.get_server_obj(server_id)
        java_flag = False
        for key in data:
            # If we don't validate the input there could be security issues
            if key == "java_selection" and data[key] != "none":
                try:
                    command = self.helper.get_execution_java(
                        data[key], server_obj.execution_command
                    )
                    setattr(server_obj, "execution_command", command)
                except ValueError:
                    return self.finish_json(
                        400,
                        {
                            "status": "error",
                            "error": "INVALID EXECUTION COMMAND",
                            "error_data": "INVALID COMMAND",
                        },
                    )
                java_flag = True

            if key != "path":
                if key == "execution_command" and java_flag:
                    continue
                setattr(server_obj, key, data[key])
        self.controller.servers.update_server(server_obj)

        self.controller.management.add_to_audit_log(
            auth_data[4]["user_id"],
            f"modified the server with ID {server_id}",
            server_id,
            self.get_remote_ip(),
        )

        return self.finish_json(200, {"status": "ok"})

    def delete(self, server_id: str):
        auth_data = self.authenticate_user()
        if not auth_data:
            return

        # DELETE /api/v2/servers/server?files=true
        remove_files = self.get_query_argument("files", None) == "true"

        if server_id not in [str(x["server_id"]) for x in auth_data[0]]:
            # if the user doesn't have access to the server, return an error
            return self.finish_json(
                400,
                {
                    "status": "error",
                    "error": "NOT_AUTHORIZED",
                    "error_data": self.helper.translation.translate(
                        "validators", "insufficientPerms", auth_data[4]["lang"]
                    ),
                },
            )
        mask = self.controller.server_perms.get_lowest_api_perm_mask(
            self.controller.server_perms.get_user_permissions_mask(
                auth_data[4]["user_id"], server_id
            ),
            auth_data[5],
        )
        server_permissions = self.controller.server_perms.get_permissions(mask)
        if EnumPermissionsServer.CONFIG not in server_permissions:
            # if the user doesn't have Config permission, return an error
            return self.finish_json(
                400,
                {
                    "status": "error",
                    "error": "NOT_AUTHORIZED",
                    "error_data": self.helper.translation.translate(
                        "validators", "insufficientPerms", auth_data[4]["lang"]
                    ),
                },
            )

        logger.info(
            (
                "Removing server and all associated files for server: "
                if remove_files
                else "Removing server from panel for server: "
            )
            + self.controller.servers.get_server_friendly_name(server_id)
        )

        self.tasks_manager.remove_all_server_tasks(server_id)
        failed = False
        for item in self.controller.servers.failed_servers[:]:
            if item["server_id"] == server_id:
                self.controller.servers.failed_servers.remove(item)
                failed = True

        if failed:
            self.controller.remove_unloaded_server(server_id)
        else:
            self.controller.remove_server(server_id, remove_files)

        self.controller.management.add_to_audit_log(
            auth_data[4]["user_id"],
            f"deleted the server {server_id}",
            server_id,
            self.get_remote_ip(),
        )

        self.finish_json(
            200,
            {"status": "ok"},
        )
