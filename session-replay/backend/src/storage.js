import { BlobServiceClient } from '@azure/storage-blob';

let _containerClient = null;

async function getContainerClient() {
  if (_containerClient) return _containerClient;

  const container = process.env.AZURE_STORAGE_CONTAINER;
  const connStr   = process.env.AZURE_STORAGE_CONNECTION_STRING;
  const account   = process.env.AZURE_STORAGE_ACCOUNT;
  const key       = process.env.AZURE_STORAGE_KEY;

  let service;

  if (connStr) {
    // Local dev / simple setup: connection string in env
    service = BlobServiceClient.fromConnectionString(connStr);
  } else if (account && key) {
    // Static credentials (not recommended in prod)
    const { StorageSharedKeyCredential } = await import('@azure/storage-blob');
    service = new BlobServiceClient(
      `https://${account}.blob.core.windows.net`,
      new StorageSharedKeyCredential(account, key)
    );
  } else {
    // AKS Workload Identity / Managed Identity — preferred in K8s
    const { DefaultAzureCredential } = await import('@azure/identity');
    service = new BlobServiceClient(
      `https://${account}.blob.core.windows.net`,
      new DefaultAzureCredential()
    );
  }

  _containerClient = service.getContainerClient(container);
  await _containerClient.createIfNotExists();
  return _containerClient;
}

export async function putObject(key, body) {
  const cc = await getContainerClient();
  const blob = cc.getBlockBlobClient(key);
  const content = typeof body === 'string' ? body : JSON.stringify(body);
  await blob.upload(content, Buffer.byteLength(content), {
    blobHTTPHeaders: { blobContentType: 'application/json' },
  });
}

export async function getObject(key) {
  const cc = await getContainerClient();
  const buffer = await cc.getBlobClient(key).downloadToBuffer();
  return JSON.parse(buffer.toString('utf-8'));
}

export async function listObjects(prefix) {
  const cc = await getContainerClient();
  const keys = [];
  for await (const item of cc.listBlobsFlat({ prefix })) {
    keys.push(item.name);
  }
  return keys;
}
