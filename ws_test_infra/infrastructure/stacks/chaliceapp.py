import os
import aws_cdk as cdk

from aws_cdk import aws_dynamodb as dynamodb

from chalice.cdk import Chalice

RUNTIME_SOURCE_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), os.pardir, "runtime")


class ChaliceApp(cdk.Stack):
    def __init__(self, scope, id, **kwargs):
        super().__init__(scope, id, **kwargs)

        # Provisioning DynamoDB
        self.ddb_messages_table = self._create_dynamodb_table("Messages", "MessagesDDB")
        self.ddb_connections_table = self._create_dynamodb_table(
            "Connections", "ConnectionsDDB", use_gsi=True
        )

        # Provisioning SAM Project(Created by AWS Chalice)
        self.chalice = Chalice(
            self,
            "ws_test_function",
            source_dir=RUNTIME_SOURCE_DIR,
            stage_config={
                "environment_variables": {
                    "CONNECTIONS_TABLE_NAME": self.ddb_connections.table_name,
                    "MESSAGES_TABLE_NAME": self.ddb_messages.table_name,
                },
            },
        )

        # DDB - Lambda grant access Role
        self.ddb_connections.grant_read_write_data(self.chalice.get_role("DefaultRole"))
        self.ddb_messages.grant_read_write_data(self.chalice.get_role("DefaultRole"))

    def _create_dynamodb_table(
        self, table_name: str, tag_name: str, use_gsi=False
    ) -> dynamodb.ITable:
        t = dynamodb.Table(
            self,
            table_name,
            table_name=table_name,
            partition_key=dynamodb.Attribute(name="PK", type=dynamodb.AttributeType.STRING),
            sort_key=dynamodb.Attribute(name="SK", type=dynamodb.AttributeType.STRING),
            removal_policy=cdk.RemovalPolicy.DESTROY,
            point_in_time_recovery=False,
            wait_for_replication_to_finish=True,  # 데이터 무결성 보장
        )

        if use_gsi:
            t.add_global_secondary_index(
                index_name="ReverseLookup",
                partition_key=dynamodb.Attribute(name="SK", type=dynamodb.AttributeType.STRING),
            )

        cdk.CfnOutput(self, tag_name, value=t.table_name)

        return t
