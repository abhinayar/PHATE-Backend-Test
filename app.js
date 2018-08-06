// ====================
// ====================
// IMPORT THE DEPS.
// ====================
// ====================

// External deps.
const path = require("path");

// Config the local env.
require("dotenv").config();

// ====================
// ====================
// CREATE THE APP
// ====================
// ====================

// Create the express app
const express = require("express"),
  // NOTE: The siofu router == socket.io file uploader
  app = express();

// Initialize Socket.io on server
const server = require("http").createServer(app),
  io = require("socket.io")(server);

// Setup the socket.io file uploader
const SocketIOFile = require("socket.io-file");

// Setup the app
app.use(express.static(__dirname + "/bower_components"));

// Serve static content
app.get("/", (req, res) => {
  res.sendFile(__dirname + "/index.html");
});

// Start the server
server.listen(3000, () => {
  console.log("Server listening on 3000");
});

// ====================
// ====================
// SETUP THE SOCKET.IO CONNECTIONS
// ====================
// ====================

// Require external packages
const uuid = require("uuid/v4");

// Generate list of connected clients
let connectedClients = {};

// Wait for client to connect
io.on("connection", client => {
  // Log new connection...
  console.log("Client connected!", client.id);
  // Add new client to the connected client list
  connectedClients[client.id] = true;
  // Log connected client list
  // console.log("Connected clients: ", Object.keys(connectedClients));

  // Setup the file upload listener
  const uploader = new SocketIOFile(client, {
    // uploadDir: {			// multiple directories
    // 	music: 'data/music',
    // 	document: 'data/document'
    // },
    uploadDir: "uploads", // simple directory
    rename: filename => {
      let file = path.parse(filename),
        { ext, name } = file,
        { PHATEClientId } = client;

      console.log("RENAME FUNCTION", file);

      return PHATEClientId ? `${PHATEClientId}${ext}` : `${name}${ext}`;
    }, // Renames the file to use the PHATE Client ID
    // accepts: ["image/png"], // chrome and some of browsers checking mp3 as 'audio/mp3', not 'audio/mpeg'
    maxFileSize: 157286400, // 150 MB. default
    chunkSize: 1024000, // default is 100KB.
    transmissionDelay: 0, // TODO: delay of each transmission, higher value saves more cpu resources, lower upload speed. default is 0(no delay)
    overwrite: true // overwrite file if exists, default is true.
  });

  // =====
  // Handle new client joining
  // and assignment of the client
  // unique ID if it has not
  // already been assigned.

  client.on("join", data => {
    console.log("CLIENT HAS JOINED, DATA: ", data || "NO DATA");

    let message = "",
      PHATEClientId;

    if (data) {
      // Set the PHATE Client ID to be the data
      PHATEClientId = data;

      message = {
        text: `Welcome back!`,
        data: data
      };
    } else {
      // Create the PHATE Client ID
      PHATEClientId = uuid();

      message = {
        text: `Welcome ${PHATEClientId}`,
        data: PHATEClientId
      };
    }

    // Set the PHATE id in the client
    client["PHATEClientId"] = PHATEClientId;

    // Emit the client id in the welcome message
    client.emit("welcome", message);
  });

  // =====
  // Handle file uploads

  uploader.on("start", fileInfo => {
    console.log(
      "FILE UPLOAD - START RECEIVING UPLOADED FILE FROM",
      client.PHATEClientId
    );
    console.log(fileInfo);
  });
  uploader.on("stream", fileInfo => {
    console.log(
      `${fileInfo.wrote} / ${fileInfo.size} BYTE(S) FROM`,
      client.PHATEClientId
    );

    // Emit the progress %
    let finishPercentage = Math.round((fileInfo.wrote / fileInfo.size) * 100);
    emitUploadProgress(finishPercentage);
  });
  uploader.on("complete", fileInfo => {
    console.log(
      "FILE FROM",
      client.PHATEClientId,
      " HAS BEEN COMPLETELY UPLOADED"
    );
    console.log(fileInfo);
  });
  uploader.on("error", err => {
    console.log(
      "AN ERROR OCCURED WHILE UPLOADING FOR",
      client.PHATEClientId,
      err
    );
  });
  uploader.on("abort", fileInfo => {
    console.log("FILE UPLOAD WAS ABORTED FOR", client.PHATEClientId, fileInfo);
  });

  // =====
  // Emit upload progress

  const emitUploadProgress = finishPercentage => {
    console.log("FILE UPLOAD % PROGRESS", finishPercentage, "%");
    client.emit("upload_progress", finishPercentage);
  };

  // =====
  // Handle client disconnect

  client.on("disconnect", () => {
    // Log the disconnecting client
    console.log(
      client.id,
      ": SOCKET ID DISCONNECTED FOR",
      client.PHATEClientId
    );
    // Delete the ref from the connected clients POJO
    delete connectedClients[client.id];
  });

  // ====================
  // ====================
  // SETUP PIP / PYTHON SCRIPT
  // ====================
  // ====================

  const { spawn, spawnSync } = require("child_process");

  const startPHATEProcessing = PHATEClientId => {
    console.log("STARTING PHATE FOR", PHATEClientId);

    // Spawn PHATE Process
    // > NOTE: We are running this like it is located
    // >> in the ./uploads directory when in reality
    // >> the script is in ./python. It's easier to
    // >> ensure the script has access to the uploads
    // >> which are a lot more dynamic than the script
    // >> itself in terms of name and location. This
    // >> might not be needed and may be a **HACK**
    const pyProcesss = spawn(
        `python ../python/${process.env.PYTHON_SCRIPT_NAME} ${PHATEClientId}`,
        {
          shell: true,
          cwd: "./uploads"
        }
      ),
      output = pyProcesss.stdout,
      error = pyProcesss.stderr;

    // On PHATE Script output
    output.on("data", data => {
      let strData = data.toString();
      console.log("PHATE SCRIPT OUTPUT: ", strData);
      client.emit("phate_message", strData);
    });

    // On PHATE Script error
    error.on("data", err => {
      let strErr = err.toString();
      console.log("PHATE SCRIPT ERROR: ", strErr);
      client.emit("phate_error", strErr);
    });

    // On PHATE Script exit
    pyProcesss.on("exit", (code, signal) => {
      let msg = `Exited PHATE processing with: ${code} - ${signal}`;
      console.log(msg.toUpperCase());

      client.emit("phate_complete", msg);
    });
  };

  startPHATEProcessing("www");
});
