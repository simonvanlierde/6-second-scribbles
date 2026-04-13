const fs = require('fs');
const path = require('path');

const enPath = path.join(__dirname, 'src', 'locales', 'en.json');
const enKeys = JSON.parse(fs.readFileSync(enPath, 'utf8'));

const filesToUpdate = ['de.json', 'es.json', 'fr.json', 'it.json'];

function deepMerge(target, source) {
  for (const key in source) {
    if (source[key] instanceof Object && key in target) {
      Object.assign(source[key], deepMerge(target[key], source[key]));
    }
  }
  Object.assign(target || {}, source);
  return target;
}

filesToUpdate.forEach(file => {
  const p = path.join(__dirname, 'src', 'locales', file);
  const data = JSON.parse(fs.readFileSync(p, 'utf8'));
  
  // Create a deep copy of enKeys, then overwrite with translated keys
  const merged = deepMerge(JSON.parse(JSON.stringify(enKeys)), data);
  
  fs.writeFileSync(p, JSON.stringify(merged, null, 2));
  console.log(`Updated ${file}`);
});
