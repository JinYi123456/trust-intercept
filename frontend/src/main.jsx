import React from "react";
import { createRoot } from "react-dom/client";
import App from "./App.jsx";
import "./index.css";

// Note: React.StrictMode is intentionally omitted so that effects which POST
// to the backend (e.g. launching the awareness coach) do not double-fire
// during development.
createRoot(document.getElementById("root")).render(<App />);
