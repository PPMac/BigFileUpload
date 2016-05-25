const min = (a, b) => (a < b ? a : b);

class FileUpload {
  constructor(file, chunkSize, threadsNumber) {
    this.file = file;
    this.chunkSize = chunkSize;
    this.threadsNumber = threadsNumber;  // number of upload threads
    this.pointer = 0;  // the next index to upload
  }

  // create file
  create() {
    $.ajax({
      url: "/file",
      method: "POST",
      headers: {
        "File-Size": this.file.size,
        "File-Name": encodeURI(this.file.name)
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
      error: (jqXHR, textStatus, errorThrown) => {
        alert(textStatus);
      }
    });
  }

  // upload chunk with index i
  uploadChunk(index) {
    let reader = new FileReader();

    reader.onload = (e) => {
      const checksum = md5(e.target.result);
      const length = e.target.result.length / this.chunkSize * this.file.size;

      let worker = new Worker("/static/js/worker.js");
      worker.postMessage([
        this.fileId, this.file, index, this.chunkSize,
        this.chunks[index], checksum
      ]);

      worker.onmessage = (e) => {
        let [key, value] = e.data;

        if (key == "chunkId") {
          this.notFinished.delete(value);

          if (this.pointer < this.chunks.length) {
            this.uploadChunk(this.pointer++);
          }

          let download = $("#download");

          if (!this.notFinished.size) {
            download.html(
              "Upload successed! You can <a href=\"/file/" +
              this.fileId + "\" download=\"" + this.file.name +
              "\">download</a> it here."
            );
          } else {
            download.html("Chunk <strong>" + value + "</strong> uploaded!");
          }
        } else if (key == "loaded") {
          $("#progress-bar").css(
            "width", (this.pointer / this.chunks.length * 100) + "%");
        }
      };
    };

    reader.readAsBinaryString(this.file.slice(
      index * this.chunkSize, (index + 1) * this.chunkSize));

    reader.onerror = (e) => {
      alert(e.target.responseText);
    };
  }

  start() {
    this.create();
  }
}


;(($) => {
  const $fileInput = $("input[type='file']");
  const $download = $("#download");
  const $progressBar = $("#progress-bar");

  $.ajax({
    url: "/",
    method: "OPTIONS",
    success: (data, textStatus, jqXHR) => {
      const chunkSize = parseInt(jqXHR.getResponseHeader("Chunk-Size"));

      $fileInput.change((e) => {
        let file = e.target.files[0];
        if (!file) return;

        $download.html("Prepare to upload......");
        $progressBar.css("width", "0%");

        // 5 threads
        const upload = new FileUpload(file, chunkSize, 5);
        upload.start();
      });
    }
  });
})(jQuery);
