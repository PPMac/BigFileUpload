class ChunkUpload {
  constructor(fileId, file, index, chunkSize, chunkId, checksum) {
    this.fileId = fileId;
    this.file = file;
    this.index = index;
    this.chunkSize = chunkSize;
    this.chunkId = chunkId;
    this.checksum = checksum;
    this.sleepTime = 500;
  }

  // create chunk
  // - upload: whether upload to server when created
  create(upload) {
    let xhr = new XMLHttpRequest();

    xhr.open("POST", "/chunk", true);
    xhr.setRequestHeader("File-Id", this.fileId);
    xhr.setRequestHeader("Chunk-Index", this.index);
    xhr.setRequestHeader("Chunk-checksum", this.checksum);

    xhr.onreadystatechange = (e) => {
      if (e.target.readyState == 4) {
        switch (e.target.status) {
        case 201:
          console.log(
            "Chunk " + this.chunkId + " with index " + this.index +
            " created " + (e.target.status >= 400 ? "failed" : "") + "!");

          if (upload) {
            this.upload();
          }
          break;

        default:
          console.log(e.target.responseText);
        }
      }
    };
    xhr.send(null);
  }

  // upload the chunk to the server
  upload() {
    let xhr = new XMLHttpRequest();

    xhr.open("HEAD", "/chunk/" + this.chunkId, true);
    xhr.send(null);

    let createSuccess = (e) => {
      this.offset = parseInt(e.target.getResponseHeader("Chunk-Offset"));

      let xhr = new XMLHttpRequest();

      xhr.open("PATCH", "/chunk/" + this.chunkId, true);
      xhr.setRequestHeader("Content-Type", "application/offset+octet-stream");
      xhr.setRequestHeader("Chunk-Offset", this.offset);

      xhr.onload = (e) => {
        if (e.target.status >= 200 && e.target.status < 300) {
          this.offset = xhr.getResponseHeader("Chunk-Offset");
          postMessage(["chunkId", this.chunkId]);
        } else {
          console.log(
            "Chunk " + this.chunkId + " with index " + this.index +
            "upload failed! try again...");

          setTimeout(this.upload(), this.sleepTime);
          this.sleepTime *= 2;
        }
      };

      xhr.upload.onprogress = (e) => {
        if (e.lengthComputable) {
          postMessage(["loaded", e.loaded]);
        }
      };
      xhr.send(this.file.slice(
        this.index * this.chunkSize + this.offset,
        (this.index + 1) * this.chunkSize));
    };

    xhr.onreadystatechange = (e) => {
      if (e.target.readyState == 4) {
        switch (e.target.status) {
        case 404:
          console.log(
            "Chunk " + this.chunkId + " with index " + this.index +
            " is not created yet, creating...");

          setTimeout(this.create(true), this.sleepTime);
          this.sleepTime *= 2;
          break;

        case 403:
          console.log("chunk file is deleted");
          break;

        default:
          createSuccess(e);
        }
      }
    };
  }
}

onmessage = (e) => {
  let [fileId, file, index, chunkSize, chunkId, checksum] = e.data;
  let chunkUpload = new ChunkUpload(
    fileId, file, index, chunkSize, chunkId, checksum);

  chunkUpload.upload();
};
