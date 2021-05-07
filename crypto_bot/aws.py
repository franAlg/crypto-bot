import boto3


class S3Connector:

    _instance = None
    _s3_resource = None
    _s3_client = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(S3Connector, cls).__new__(cls)
            # Put any initialization here.
        return cls._instance

    def __init__(self) -> None:
        print("Creating S3 resource...")
        self._s3_resource = boto3.resource(service_name="s3")
        self._s3_client = boto3.client(service_name="s3")

    def get_object(self, bucket_name, object):
        return self._s3_resource.Bucket(bucket_name).Object(object).get()

    def put_object(
        self, bucket_name, object, data: str = "", empty: bool = False
    ):
        if empty:
            self._s3_client.delete_object(Bucket=bucket_name, Key=object)
            self._s3_client.put_object(Bucket=bucket_name, Key=object)
        else:
            self._s3_resource.Object(bucket_name, object).put(
                Body=str(data).encode("utf_8")
            )

    def append_to_object(self, bucket_name, object, data: str):
        data = str(data)
        object_data = self.get_object(bucket_name, object)

        object_content = []
        for line in object_data["Body"].iter_lines():
            object_content.append(line.decode("utf-8"))
        object_content.append(data)

        updated_content = "\n".join(object_content)
        self.put_object(bucket_name, object, updated_content)


S3 = S3Connector()