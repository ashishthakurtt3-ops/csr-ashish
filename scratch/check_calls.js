const fs = require('fs');
const content = fs.readFileSync('static/js/app.js', 'utf8');
const lines = content.split('\n');
lines.forEach((l, idx) => {
  if (l.includes('openJobDetailsModal')) {
    console.log(idx + 1, l.trim());
  }
});
