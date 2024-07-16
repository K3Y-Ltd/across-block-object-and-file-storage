import io
from minio import Minio
from minio.error import S3Error
from dotenv import load_dotenv
from fastapi import FastAPI, UploadFile, HTTPException, Response, File, Path, Form
from fastapi.routing import APIRouter
import os
import json

load_dotenv()

MINIO_ADDRESS = os.getenv("MINIO_ADDRESS")
MINIO_ACCESS_KEY = os.getenv("MINIO_ACCESS_KEY")
MINIO_SECRET_KEY = os.getenv("MINIO_SECRET_KEY")

# Name of buckets used for Block Object & File Storage Service
PCAP = 'pcap'

# Name of buckets used for Analytics model repository
PFCPFLOWMETER = 'pfcpflowmeter'
CICFLOWMETER = 'cicflowmeter'
TSTAT = 'tstat'

# Create Minio Client
minio_client = Minio(
    MINIO_ADDRESS,
    access_key=MINIO_ACCESS_KEY,
    secret_key=MINIO_SECRET_KEY,
    secure=False
)

# Admin Router
admin_router = APIRouter(prefix="/admin", tags=["admin"])

# Block Object and File Storage
block_object_router = APIRouter(prefix="/pcap", tags=["pcap"])

# analytics_router = APIRouter(prefix="/analytics", tags=["Analytics-Repository"])
tstat_router = APIRouter(prefix="/tstat", tags=["tstat"])
pfcpflowmeter_router = APIRouter(prefix="/pfcpflowmeter", tags=["pfcpflowmeter"])
cicflowmeter_router = APIRouter(prefix="/cicflowmeter", tags=["cicflowmeter"])



# Create a FastAPI instance
app = FastAPI(
    # openapi_tags=tags_metadata,
    openapi_url="/api/v1/openapi.json",  # Specify a custom OpenAPI JSON path

)

@app.get("/", tags=["API"])
async def healthcheck():
    """
    Healthcheck endpoint
    """
    return {"message": "Server is up"}

# ---------------- Admin Endpoints --------------------------
# This section provides the ADMIN endpoint to:
# - Create buckets
# - Delete buckets
# - Upload file in the specified bucket
# - Download file in the specified bucket
# - Get file metadata in the specified bucket
# - Delete file in the specified bucket

@admin_router.get("/")
async def list_all_buckets():
    """
    List all buckets
    """
    try:
        buckets = minio_client.list_buckets()
        bucket_names = [bucket.name for bucket in buckets]
        return {"buckets": bucket_names}
    except S3Error as e:
        raise HTTPException(status_code=500, detail="Error listing buckets")

@admin_router.post("/buckets")
async def create_bucket(bucket_name: str = Form(...)):
    """
    Create a new bucket
    """
    try:
        if not minio_client.bucket_exists(bucket_name):
            minio_client.make_bucket(bucket_name)
            return {"message": f"Bucket '{bucket_name}' created successfully"}
        else:
            raise HTTPException(status_code=400, detail="Bucket already exist")
    except S3Error as e:
        raise HTTPException(status_code=500, detail="Error creating bucket")

@admin_router.delete("/buckets/{bucket_name}")
async def delete_bucket(bucket_name: str):
    """
    Delete a bucket if empty
    """
    try:
        if minio_client.bucket_exists(bucket_name):
            objects = list(minio_client.list_objects(bucket_name, recursive=True))
            if objects:
                raise HTTPException(status_code=400, detail="Bucket is not empty")
            else:
                minio_client.remove_bucket(bucket_name)
                return {"message": f"Bucket '{bucket_name}' deleted successfully"}
        else:
            raise HTTPException(status_code=404, detail="Bucket not found")
    except S3Error as e:
        raise HTTPException(status_code=500, detail="Error deleting bucket")

# --------- CRUD Operations for Files -----------
@app.get("/{bucket_name}/files")
async def list_files(bucket_name: str):
    """
    List all files in a specified bucket
    """
    try:
        objects = minio_client.list_objects(bucket_name, recursive=True)
        file_names = [obj.object_name for obj in objects]
        return {"files": file_names}
    except S3Error as e:
        raise HTTPException(status_code=404, detail="Bucket not found or is empty")

@app.post("/{bucket_name}/files")
async def upload_file(bucket_name: str, file: UploadFile = File(...), metadata: str = Form(default="")):
    """
    Upload a file to a specified bucket
    """
    try:
        file_contents = await file.read()
        content_length = len(file_contents)
        file_bytes = io.BytesIO(file_contents)

        # Save the file to Minio
        minio_client.put_object(
            bucket_name,
            file.filename,
            file_bytes,
            content_length,
            metadata={"metadata": metadata} if metadata else None
        )
        return {"message": "File uploaded successfully"}
    except S3Error as e:
        raise HTTPException(status_code=500, detail="Failed to upload file")

@app.get("/{bucket_name}/files/{filename}")
async def get_file(bucket_name: str, filename: str):
    """
    Retrieve a file from a specified bucket
    """
    try:
        # Retrieve the file from Minio
        response = minio_client.get_object(
            bucket_name,
            filename,
        )
        return Response(content=response.read(), media_type=response.headers["Content-Type"])
    except S3Error as e:
        raise HTTPException(status_code=404, detail="File not found")

@app.get("/{bucket_name}/files/{filename}/metadata")
async def get_file_metadata(bucket_name: str, filename: str = Path(...)):
    """
    Get file metadata from a specified bucket
    """
    try:
        # Stats of the object in the specified bucket.
        object_info = minio_client.stat_object(bucket_name, filename)
        if 'x-amz-meta-metadata' in object_info.metadata:
            metadata_value = object_info.metadata['x-amz-meta-metadata']

            # Check if the value is not None before returning
            if metadata_value is not None:
                return {"metadata": metadata_value}

        return {"metadata": {}}
    except S3Error as e:
        raise HTTPException(status_code=404, detail="Bucket or file not found")

@app.delete("/{bucket_name}/files/{filename}")
async def delete_file(bucket_name: str, filename: str):
    """
    Delete a file from a specified bucket
    """
    try:
        # Check if file exists
        file = minio_client.stat_object(bucket_name, filename)

        if not file:
            raise HTTPException(status_code=404, detail="File not found")

        minio_client.remove_object(bucket_name, filename)
        return {"message": "File deleted"}
    except S3Error as e:
        raise HTTPException(status_code=404, detail="File not found")

# ---------------- PCAP Files --------------------------

@block_object_router.get("/")
async def list_pcap_files():
    """
    List all pcap files in Block Object & File Storeage
    """
    try:
        objects = minio_client.list_objects(PCAP, recursive=True)

        file_names = [obj.object_name for obj in objects]

        return {"files": file_names}
    except S3Error as e:
        raise HTTPException(status_code=404, detail="Bucket not found or is empty")

@block_object_router.post("/")
async def upload_pcap_file(file: UploadFile = File(...), metadata: str = Form(default="")):
    """
    Uploads a pcap file to Block Object & File Storeage
    """
    try:
        file_contents = await file.read()
        content_length = len(file_contents)
        file_bytes = io.BytesIO(file_contents)

        # Save the file to Minio
        minio_client.put_object(
            PCAP,
            file.filename,
            file_bytes,
            content_length,
            metadata={"metadata": metadata} if metadata else None
        )
        return {"message": "File uploaded successfully"}
    except S3Error as e:
        raise HTTPException(status_code=500, detail="Failed to upload file")

@block_object_router.get("/{filename}")
async def get_pcap_file(filename: str):
    """
    Retrieves a file from Block Object & File Storeage
    """
    try:
        # Retrieve the file from Minio
        response = minio_client.get_object(
            PCAP,
            filename,
        )
        return Response(content=response.read(), media_type=response.headers["Content-Type"])
    except S3Error as e:
        raise HTTPException(status_code=404, detail="File not found")

@block_object_router.get("/{filename}/metadata")
async def get_pcap_file_metadata(filename: str = Path(...)):
    """
    Get file Metadata from Block Object & File Storeage
    """
    try:
        # Stats of the object in the specified bucket.
        object_info = minio_client.stat_object(PCAP, filename)
        if 'x-amz-meta-metadata' in object_info.metadata:
            metadata_value = object_info.metadata['x-amz-meta-metadata']

            # Check if the value is not None before returning
            if metadata_value is not None:
                return {"metadata": metadata_value}

        return {"metadata": {}}
    except S3Error as e:
        raise HTTPException(status_code=404, detail="Bucket not found or is empty")

@block_object_router.delete("/{filename}")
async def delete_pcap_file(filename: str):
    """
    Deletes a file from Block Object & File Storeage
    """
    try:
        # Check if file exists
        file = minio_client.stat_object(PCAP, filename)

        if not file:
            raise HTTPException(status_code=404, detail="File not found")

        minio_client.remove_object(PCAP, filename)
        return {"message": "File deleted"}
    except S3Error as e:
        raise HTTPException(status_code=404, detail="File not found")

# ---------------- Analytics Model Repository --------------------------

# --------- Tstat -----------

@tstat_router.get("/files")
async def list_analytics_tstat_files():
    """
    Lists all files in Analytics - Tstat
    """
    try:
        # List all objects in the bucket
        objects = minio_client.list_objects(TSTAT, recursive=True)

        # Extract file names from the objects list
        file_names = [obj.object_name for obj in objects]

        return {"files": file_names}
    except S3Error as e:
        raise HTTPException(status_code=404, detail="Bucket not found or is empty")

@tstat_router.post("/files")
async def upload_analytics_tstat_file(file: UploadFile = File(...), metadata: str = Form(default="")):
    """
    Uploads a file to Analytics - Tstat
    """
    try:
        file_contents = await file.read()
        content_length = len(file_contents)
        file_bytes = io.BytesIO(file_contents)

        # Save the file to Minio
        minio_client.put_object(
            TSTAT,
            file.filename,
            file_bytes,
            content_length,
            metadata={"metadata": metadata} if metadata else None
        )
        return {"message": "File uploaded successfully"}
    except S3Error as e:
        raise HTTPException(status_code=500, detail="Failed to upload file")

@tstat_router.get("/files/{filename}")
async def get_analytics_tstat_file(filename: str):
    """
    Retrieves a file from Analytics - Tstat
    """
    try:
        # Retrieve the file from Minio
        response = minio_client.get_object(
            TSTAT,
            filename,
        )
        return Response(content=response.read(), media_type=response.headers["Content-Type"])
    except S3Error as e:
        raise HTTPException(status_code=404, detail="File not found")

@tstat_router.get("/files/{filename}/metadata")
async def get_analytics_tstat_file_metadata(filename: str = Path(...)):
    """
    Get file Metadata from Analytics - Tstat
    """
    try:
        # Stats of the object in the specified bucket.
        object_info = minio_client.stat_object(TSTAT, filename)
        if 'x-amz-meta-metadata' in object_info.metadata:
            metadata_value = object_info.metadata['x-amz-meta-metadata']

            # Check if the value is not None before returning
            if metadata_value is not None:
                return {"metadata": metadata_value}

        return {"metadata": {}}
    except S3Error as e:
        raise HTTPException(status_code=404, detail="Bucket not found or is empty")

@tstat_router.delete("/files/{filename}")
async def delete_analytics_file(filename: str):
    """
    Deletes a file from Analytics - Tstat
    """
    try:
        # Check if file exists
        file = minio_client.stat_object(TSTAT, filename)

        if not file:
            raise HTTPException(status_code=404, detail="File not found")

        minio_client.remove_object(TSTAT, filename)
        return {"message": "File deleted"}
    except S3Error as e:
        raise HTTPException(status_code=404, detail="File not found")

# --------- Pfcpflowmeter -----------

@pfcpflowmeter_router.get("/files")
async def list_analytics_pfcpflowmeter_files():
    """
    Lists all files in Analytics - Pfcpflowmeter
    """
    try:
        # List all objects in the bucket
        objects = minio_client.list_objects(PFCPFLOWMETER, recursive=True)

        # Extract file names from the objects list
        file_names = [obj.object_name for obj in objects]

        return {"files": file_names}
    except S3Error as e:
        raise HTTPException(status_code=404, detail="Bucket not found or is empty")

@pfcpflowmeter_router.post("/files")
async def upload_analytics_pfcpflowmeter_file(file: UploadFile = File(...), metadata: str = Form(default="")):
    """
    Uploads a file to Analytics - Pfcpflowmeter
    """
    try:
        file_contents = await file.read()
        content_length = len(file_contents)
        file_bytes = io.BytesIO(file_contents)

        # Save the file to Minio
        minio_client.put_object(
            PFCPFLOWMETER,
            file.filename,
            file_bytes,
            content_length,
            metadata={"metadata": metadata} if metadata else None
        )
        return {"message": "File uploaded successfully"}
    except S3Error as e:
        raise HTTPException(status_code=500, detail="Failed to upload file")

@pfcpflowmeter_router.get("/files/{filename}")
async def get_analytics_pfcfpflowmeter_file(filename: str):
    """
    Retrieves a file from Analytics - Tstat
    """
    try:
        # Retrieve the file from Minio
        response = minio_client.get_object(
            PFCPFLOWMETER,
            filename,
        )
        return Response(content=response.read(), media_type=response.headers["Content-Type"])
    except S3Error as e:
        raise HTTPException(status_code=404, detail="File not found")

@pfcpflowmeter_router.get("/files/{filename}/metadata")
async def get_analytics_pfcpflowmeter_file_metadata(filename: str = Path(...)):
    """
    Get file Metadata from Analytics - Pfcpflowmeter
    """
    try:
        # Stats of the object in the specified bucket.
        object_info = minio_client.stat_object(PFCPFLOWMETER, filename)
        if 'x-amz-meta-metadata' in object_info.metadata:
            metadata_value = object_info.metadata['x-amz-meta-metadata']

            # Check if the value is not None before returning
            if metadata_value is not None:
                return {"metadata": metadata_value}

        return {"metadata": {}}
    except S3Error as e:
        raise HTTPException(status_code=404, detail="Bucket not found or is empty")

@pfcpflowmeter_router.delete("/files/{filename}")
async def delete_analytics_file(filename: str):
    """
    Deletes a file from Analytics - Pfcpflowmeter
    """
    try:
        # Check if file exists
        file = minio_client.stat_object(PFCPFLOWMETER, filename)

        if not file:
            raise HTTPException(status_code=404, detail="File not found")

        minio_client.remove_object(PFCPFLOWMETER, filename)
        return {"message": "File deleted"}
    except S3Error as e:
        raise HTTPException(status_code=404, detail="File not found")


# --------- Cicflowmeter -----------

@cicflowmeter_router.get("/files")
async def list_analytics_cicflowmeter_files():
    """
    Lists all files in Analytics - Cicflowmeter
    """
    try:
        # List all objects in the bucket
        objects = minio_client.list_objects(CICFLOWMETER, recursive=True)

        # Extract file names from the objects list
        file_names = [obj.object_name for obj in objects]

        return {"files": file_names}
    except S3Error as e:
        raise HTTPException(status_code=404, detail="Bucket not found or is empty")

@cicflowmeter_router.post("/files")
async def upload_analytics_cicflowmeter_file(file: UploadFile = File(...), metadata: str = Form(default="")):
    """
    Uploads a file to Analytics - Cicflowmeter
    """
    try:
        file_contents = await file.read()
        content_length = len(file_contents)
        file_bytes = io.BytesIO(file_contents)

        # Save the file to Minio
        minio_client.put_object(
            CICFLOWMETER,
            file.filename,
            file_bytes,
            content_length,
            metadata={"metadata": metadata} if metadata else None
        )
        return {"message": "File uploaded successfully"}
    except S3Error as e:
        raise HTTPException(status_code=500, detail="Failed to upload file")

@cicflowmeter_router.get("/files/{filename}")
async def get_analytics_cicflowmeter_file(filename: str):
    """
    Retrieves a file from Analytics - Tstat
    """
    try:
        # Retrieve the file from Minio
        response = minio_client.get_object(
            CICFLOWMETER,
            filename,
        )
        return Response(content=response.read(), media_type=response.headers["Content-Type"])
    except S3Error as e:
        raise HTTPException(status_code=404, detail="File not found")

@cicflowmeter_router.get("/files/{filename}/metadata")
async def get_analytics_tstat_file_metadata(filename: str = Path(...)):
    """
    Get file Metadata from Analytics - Cicflowmeter
    """
    try:
        # Stats of the object in the specified bucket.
        object_info = minio_client.stat_object(CICFLOWMETER, filename)
        if 'x-amz-meta-metadata' in object_info.metadata:
            metadata_value = object_info.metadata['x-amz-meta-metadata']

            # Check if the value is not None before returning
            if metadata_value is not None:
                return {"metadata": metadata_value}

        return {"metadata": {}}
    except S3Error as e:
        raise HTTPException(status_code=404, detail="Bucket not found or is empty")

@cicflowmeter_router.delete("/files/{filename}")
async def delete_analytics_file(filename: str):
    """
    Deletes a file from Analytics - Cicflowmeter
    """
    try:
        # Check if file exists
        file = minio_client.stat_object(CICFLOWMETER, filename)

        if not file:
            raise HTTPException(status_code=404, detail="File not found")

        minio_client.remove_object(CICFLOWMETER, filename)
        return {"message": "File deleted"}
    except S3Error as e:
        raise HTTPException(status_code=404, detail="File not found")

app.include_router(tstat_router, prefix="/analytics", tags=["tstat"])
app.include_router(pfcpflowmeter_router, prefix="/analytics", tags=["pfcpflowmeter"])
app.include_router(cicflowmeter_router, prefix="/analytics", tags=["cicflowmeter"])

app.include_router(block_object_router)
app.include_router(admin_router)