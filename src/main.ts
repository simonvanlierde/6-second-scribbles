import './assets/main.css'

import { createPinia } from 'pinia'
import { createApp } from 'vue'

import App from './App.vue'
import fontawesomePlugin from './plugins/fontawesome'
import loggerPlugin from './plugins/logger'
import router from './router'

const app = createApp(App)

app.use(createPinia())
app.use(router)
app.use(loggerPlugin)
app.use(fontawesomePlugin)

app.mount('#app')
