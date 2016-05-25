class ChunkUpload {
  constructor(fileId, file, index, chunkId, checksum) {
    this.fileId = fileId;
    this.file = file;
    this.index = index;
    this.chunkId = chunkId;
    this.checksum = checksum;
    this.sleepTime = 500;
  }

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

  upload() {
    let xhr = new XMLHttpRequest();

    xhr.open("HEAD", "/chunk/" + this.chunkId, true);
    xhr.send(null);

    let createSuccess = (e) => {
      this.chunkSize = parseInt(e.target.getResponseHeader("Chunk-Size"));
      this.offset = parseInt(e.target.getResponseHeader("Chunk-Offset"));

      let reader = new FileReader();

      reader.onload = (e) => {
        if (!e.target.result) return;

        let patchXhr = new XMLHttpRequest();

        patchXhr.open("PATCH", "/chunk/" + this.chunkId, true);
        patchXhr.overrideMimeType("application/octet-stream");
        patchXhr.setRequestHeader("Chunk-Offset", this.offset);

        patchXhr.onload = (e) => {
          if (e.target.status >= 200 && e.target.status < 300) {
            this.offset = patchXhr.getResponseHeader("Chunk-Offset");
            postMessage(this.chunkId);
          } else {
            console.log(
              "Chunk " + this.chunkId + " with index " + this.index +
              "upload failed! try again...");

            setTimeout(this.upload(), this.sleepTime);
            this.sleepTime *= 2;
          }
        };

        patchXhr.send(e.target.result);
      };

      reader.readAsBinaryString(this.file.slice(
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
  let [fileId, file, index, chunkId, checksum] = e.data;
  let chunkUpload = new ChunkUpload(fileId, file, index, chunkId, checksum);
  chunkUpload.upload();
};
