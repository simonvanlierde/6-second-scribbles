import { library } from '@fortawesome/fontawesome-svg-core'
import { fab } from '@fortawesome/free-brands-svg-icons'
import { fas } from '@fortawesome/free-solid-svg-icons'
import { FontAwesomeIcon } from '@fortawesome/vue-fontawesome'

// Add whole free styles so icons can be referenced by string (e.g. "fa-solid fa-trophy")
// Cast to any to satisfy library.add types for entire packs
library.add(fas as any, fab as any)

export default {
  install(app: any) {
    // register lowercase kebab-case name like the docs recommend
    app.component('font-awesome-icon', FontAwesomeIcon)
  },
}
