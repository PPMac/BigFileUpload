const min = (a, b) => (a < b ? a : b);

class FileUpload {
  constructor(file, chunkSize, threadsNumber) {
    this.file = file;
    this.chunkSize = chunkSize;
    this.threadsNumber = threadsNumber;
    this.pointer = 0;
  }

  create() {
    $.ajax({
      url: "/file",
      method: "POST",
      headers: {
        "File-Size": this.file.size
      },
      success: (data, textStatus, jqXHR) =>  {
        this.fileId = jqXHR.getResponseHeader("File-Id");
        this.chunks = jqXHR.getResponseHeader("File-Chunks").split(" ");
        this.location = jqXHR.getResponseHeader("Location");

        this.notFinished = new Set(this.chunks);

        for (; this.pointer < min(this.chunks.length, this.threadsNumber);
             ++this.pointer) {
          this.uploadChunk(this.pointer);
        }
      },
      error: (jqXHR) => {
        alert("upload failed");
      }
    });
  }

  uploadChunk(index) {
    let reader = new FileReader();

    reader.onload = (e) => {
      const checksum = md5(e.target.result);

      let worker = new Worker("/static/js/worker.js");
      worker.postMessage(
        [this.fileId, this.file, index, this.chunks[index], checksum]);

      worker.onmessage = (e) => {
        this.notFinished.delete(e.data);

        if (this.pointer < this.chunks.length) {
          this.uploadChunk(this.pointer++);
        }

        if (!this.notFinished.size) {
          let download = $("#download");
          download.html("<a href=\"/file/" + this.fileId + "\" download>Download</a>");
        }
      };
    };

    reader.readAsBinaryString(this.file.slice(
      index * this.chunkSize, (index + 1) * this.chunkSize));

    reader.onerror = () => {
      alert("read failed");
    };
  }

  start() {
    this.create();
  }
}


;(($) => {
  const $fileInput = $("input[type='file']");

  $.ajax({
    url: "/",
    method: "OPTIONS",
    success: (data, textStatus, jqXHR) => {
      const chunkSize = parseInt(jqXHR.getResponseHeader("Chunk-Size"));

      $fileInput.change((e) => {
        let file = e.target.files[0];
        if (!file) return;

        const upload = new FileUpload(file, chunkSize, 3);
        upload.start();
      });
    }
  });

})(jQuery);
