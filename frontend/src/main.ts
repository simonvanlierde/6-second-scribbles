import "./assets/main.css";

import { createPinia } from "pinia";
import { createPersistedState } from "pinia-plugin-persistedstate";
import { createApp } from "vue";

import App from "./App.vue";
import { i18n } from "./i18n";
import router from "./router";

const app = createApp(App);

const pinia = createPinia();
pinia.use(createPersistedState());

app.use(pinia);
app.use(router);
app.use(i18n);

app.mount("#app");
