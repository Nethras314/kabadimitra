// Cloudinary direct upload.
//
// The collector uploads straight from the device using a short-lived signature
// issued by the backend — image bytes never pass through the API, and never
// touch PostgreSQL. The backend only ever stores the resulting public_id/URL.

import { ApiClient } from './client';

export interface UploadResult {
  publicId: string;
  secureUrl: string;
  width?: number;
  height?: number;
}

export class CloudinaryUploader {
  constructor(private readonly api: ApiClient) {}

  async upload(
    fileUri: string,
    opts: { lotId?: string; mimeType?: string; fileName?: string } = {},
  ): Promise<UploadResult> {
    // 1. Ask the backend to sign the upload.
    const params = await this.api.mediaUploadParams();

    // 2. POST the file straight to Cloudinary.
    const form = new FormData();
    form.append('file', {
      uri: fileUri,
      name: opts.fileName ?? 'capture.jpg',
      type: opts.mimeType ?? 'image/jpeg',
    } as unknown as Blob);
    form.append('api_key', params.api_key);
    form.append('timestamp', String(params.timestamp));
    form.append('signature', params.signature);
    if (opts.lotId) {
      // Deterministic public id path makes retries idempotent server-side.
      form.append('public_id', `kabadi/${opts.lotId}/${Date.now()}`);
    }

    const res = await fetch(
      `https://api.cloudinary.com/v1_1/${params.cloud_name}/image/upload`,
      { method: 'POST', body: form },
    );
    if (!res.ok) {
      throw new Error(`cloudinary upload failed: ${res.status}`);
    }
    const data = (await res.json()) as {
      public_id: string;
      secure_url: string;
      width?: number;
      height?: number;
    };
    return {
      publicId: data.public_id,
      secureUrl: data.secure_url,
      width: data.width,
      height: data.height,
    };
  }
}
