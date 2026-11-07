import "./lib/zodConfig";
import "./assets/main.css";
import { mount } from "svelte";
import App from "./App.svelte";
import { startRouter } from "./router";

startRouter();
mount(App, { target: document.getElementById("app")! });
