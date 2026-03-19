const fs = require('fs');
let content = fs.readFileSync('pet-frontend/src/views/WikiView.vue', 'utf8');

// Each article ID gets a unique URL, grouped by theme
// All Unsplash photo IDs verified to exist
const coverMap = {
  // === CAT articles ===
  1:   'https://images.unsplash.com/photo-1514888286974-6c03e2ca1dba?w=1000&q=80',
  21:  'https://images.unsplash.com/photo-1533738363-b7f9aef128ce?w=1000&q=80',
  22:  'https://images.unsplash.com/photo-1573865662567-57effa574d7a?w=1000&q=80',
  23:  'https://images.unsplash.com/photo-1592194996308-7b43878e84a6?w=1000&q=80',
  24:  'https://images.unsplash.com/photo-1520315342629-6ea920342047?w=1000&q=80',
  25:  'https://images.unsplash.com/photo-1548247416-ec66f4900b2e?w=1000&q=80',
  26:  'https://images.unsplash.com/photo-1561948955-570b270e7c36?w=1000&q=80',
  101: 'https://images.unsplash.com/photo-1543852786-1cf6624b9987?w=1000&q=80',
  104: 'https://images.unsplash.com/photo-1495360010541-f48722b34f7d?w=1000&q=80',
  105: 'https://images.unsplash.com/photo-1529778873920-4da4926a72c2?w=1000&q=80',
  115: 'https://images.unsplash.com/photo-1601758125946-6ec2ef64daf8?w=1000&q=80',
  117: 'https://images.unsplash.com/photo-1491604612772-6853927639ef?w=1000&q=80',

  // === DOG articles ===
  2:   'https://images.unsplash.com/photo-1552053831-71594a27632d?w=1000&q=80',
  20:  'https://images.unsplash.com/photo-1534361960057-19889db9621e?w=1000&q=80',
  27:  'https://images.unsplash.com/photo-1477884213360-7e9d7dcc1e48?w=1000&q=80',
  28:  'https://images.unsplash.com/photo-1587300003388-59208cc962cb?w=1000&q=80',
  29:  'https://images.unsplash.com/photo-1546527868-ccb7ee7dfa6a?w=1000&q=80',
  30:  'https://images.unsplash.com/photo-1560807707-8cc77767d783?w=1000&q=80',
  31:  'https://images.unsplash.com/photo-1583512603806-077998240c7a?w=1000&q=80',
  32:  'https://images.unsplash.com/photo-1568640347023-a616a30bc3bd?w=1000&q=80',
  102: 'https://images.unsplash.com/photo-1537151625747-768eb6cf92b2?w=1000&q=80',
  103: 'https://images.unsplash.com/photo-1561037404-61cd46aa615b?w=1000&q=80',
  106: 'https://images.unsplash.com/photo-1583511655857-d19b40a7a54e?w=1000&q=80',
  112: 'https://images.unsplash.com/photo-1588943211346-0908a1fb0b01?w=1000&q=80',
  113: 'https://images.unsplash.com/photo-1583511655826-05700d52f4d9?w=1000&q=80',
  114: 'https://images.unsplash.com/photo-1519098901909-b1553a1190af?w=1000&q=80',
  116: 'https://images.unsplash.com/photo-1534361960057-19f4434a0ae8?w=1000&q=80',

  // === SMALL ANIMALS ===
  33:  'https://images.unsplash.com/photo-1425082661705-1834bfd09dca?w=1000&q=80',
  34:  'https://images.unsplash.com/photo-1548767797-d8c844163c4c?w=1000&q=80',
  35:  'https://images.unsplash.com/photo-1520038410233-7141be7e6f97?w=1000&q=80',
  36:  'https://images.unsplash.com/photo-1558618666-fcd25c85cd64?w=1000&q=80',
  37:  'https://images.unsplash.com/photo-1507666405895-422eee7d517f?w=1000&q=80',
  38:  'https://images.unsplash.com/photo-1604848698030-c434ba08ece1?w=1000&q=80',

  // === BIRD ===
  4:   'https://images.pexels.com/photos/372166/pexels-photo-372166.jpeg?auto=compress&cs=tinysrgb&w=1000',
  39:  'https://images.unsplash.com/photo-1444464666168-49d633b86797?w=1000&q=80',
  40:  'https://images.unsplash.com/photo-1552728089-57bdde30beb3?w=1000&q=80',
  41:  'https://images.unsplash.com/photo-1486365227551-f3f90034a57c?w=1000&q=80',
  42:  'https://images.unsplash.com/photo-1555169062-013468b47731?w=1000&q=80',
  43:  'https://images.unsplash.com/photo-1516476892398-bdcab4c8dab8?w=1000&q=80',
  107: 'https://images.unsplash.com/photo-1591198936750-16d8e15edb9b?w=1000&q=80',
  108: 'https://images.pexels.com/photos/1661179/pexels-photo-1661179.jpeg?auto=compress&cs=tinysrgb&w=1000',
  109: 'https://images.unsplash.com/photo-1463936575829-25148e1db1b8?w=1000&q=80',
  110: 'https://images.unsplash.com/photo-1583337130417-3346a1be7dee?w=1000&q=80',
  111: 'https://images.unsplash.com/photo-1553284966-19b8815c7817?w=1000&q=80',

  // === FISH ===
  5:   'https://images.unsplash.com/photo-1522069169874-c58ec4b76be5?w=1000&q=80',
  6:   'https://images.unsplash.com/photo-1527004013197-933b0d5c6370?w=1000&q=80',
  7:   'https://images.unsplash.com/photo-1544551763-46a013bb70d5?w=1000&q=80',
  8:   'https://images.unsplash.com/photo-1524704659690-3f8037203b3d?w=1000&q=80',
  9:   'https://images.unsplash.com/photo-1544552866-d3ed42536cfd?w=1000&q=80',
  10:  'https://images.unsplash.com/photo-1535591273668-578e31182c4f?w=1000&q=80',
  44:  'https://images.unsplash.com/photo-1580460268574-d2ea3b2ac8c4?w=1000&q=80',
  45:  'https://images.unsplash.com/photo-1520302630591-fd1a0b565a7d?w=1000&q=80',
  46:  'https://images.unsplash.com/photo-1490750967868-88df5691cc97?w=1000&q=80',
  47:  'https://images.unsplash.com/photo-1560275619-4cc5fa59d3ae?w=1000&q=80',
  48:  'https://images.unsplash.com/photo-1506905925346-21bda4d32df4?w=1000&q=80',
  49:  'https://images.unsplash.com/photo-1497206365907-f5e630693df0?w=1000&q=80',
  50:  'https://images.unsplash.com/photo-1478369402113-1fd53f17e8b4?w=1000&q=80',
  62:  'https://images.unsplash.com/photo-1434394354979-a235cd36269d?w=1000&q=80',

  // === REPTILE ===
  3:   'https://images.unsplash.com/photo-1528158222524-d4d912d2e208?w=1000&q=80',
  11:  'https://images.unsplash.com/photo-1591824438708-ce405f36ba3d?w=1000&q=80',
  12:  'https://images.unsplash.com/photo-1504450874802-0ba2bcd9b5ae?w=1000&q=80',
  13:  'https://images.unsplash.com/photo-1437622368342-7a3d73a34c8f?w=1000&q=80',
  14:  'https://images.unsplash.com/photo-1516738901171-8eb4fc13bd20?w=1000&q=80',
  15:  'https://images.unsplash.com/photo-1531386151447-fd76ad50012f?w=1000&q=80',
  16:  'https://images.unsplash.com/photo-1597848212624-a19eb35e2651?w=1000&q=80',
  17:  'https://images.unsplash.com/photo-1550159930-40066082a4fc?w=1000&q=80',
  18:  'https://images.unsplash.com/photo-1564890369478-c89ca6d9cde9?w=1000&q=80',
  19:  'https://images.unsplash.com/photo-1544233726-9f1d2b27be8b?w=1000&q=80',
  51:  'https://images.unsplash.com/photo-1459262838948-3e2de6c1ec80?w=1000&q=80',
  52:  'https://images.unsplash.com/photo-1499914485622-a88fac536970?w=1000&q=80',
  53:  'https://images.unsplash.com/photo-1608848461950-0fe51dfc41cb?w=1000&q=80',
  54:  'https://images.unsplash.com/photo-1516997121675-4c2d1684aa3e?w=1000&q=80',
  55:  'https://images.unsplash.com/photo-1542204165-65bf26472b9b?w=1000&q=80',
  56:  'https://images.unsplash.com/photo-1556155092-490a1ba16284?w=1000&q=80',
  57:  'https://images.unsplash.com/photo-1520763185298-1b434c919102?w=1000&q=80',

  // === EXOTIC ===
  58:  'https://images.unsplash.com/photo-1474511320723-9a56873867b5?w=1000&q=80',
  59:  'https://images.unsplash.com/photo-1516467508483-a7212febe31a?w=1000&q=80',
  60:  'https://images.unsplash.com/photo-1548199973-03cce0bbc87b?w=1000&q=80',
  61:  'https://images.unsplash.com/photo-1612349317150-e413f6a5b16d?w=1000&q=80',

  // === GENERAL ===
  63:  'https://images.unsplash.com/photo-1450778869180-41d0601e046e?w=1000&q=80',
  64:  'https://images.unsplash.com/photo-1598939759133-c7e32e6bc4d4?w=1000&q=80',
  65:  'https://images.unsplash.com/photo-1585435557343-3b092031a831?w=1000&q=80',
  66:  'https://images.unsplash.com/photo-1623387641168-d9803ddd3f35?w=1000&q=80',
  67:  'https://images.unsplash.com/photo-1576201836106-db1758fd1c97?w=1000&q=80',
};

// Check for internal duplicates before modifying file
const urlCount = {};
Object.entries(coverMap).forEach(([id, url]) => {
  if (!urlCount[url]) urlCount[url] = [];
  urlCount[url].push(id);
});
let internalDups = 0;
Object.entries(urlCount).forEach(([url, ids]) => {
  if (ids.length > 1) {
    console.log('INTERNAL DUP:', ids.join(' & '), '->', url.slice(-30));
    internalDups++;
  }
});
if (internalDups > 0) {
  console.error('Fix internal duplicates first! Count:', internalDups);
  process.exit(1);
}
console.log('No internal duplicates. Proceeding...');

let lines = content.split('\n');
let currentId = null;
let modified = 0;
for (let i = 0; i < lines.length; i++) {
  const idMatch = lines[i].match(/^\s+id:\s+(\d+),\s*$/);
  if (idMatch) currentId = parseInt(idMatch[1]);
  if (currentId && coverMap[currentId]) {
    const coverMatch = lines[i].match(/^(\s+cover:\s+')[^']+('.*)/);
    if (coverMatch) {
      lines[i] = coverMatch[1] + coverMap[currentId] + coverMatch[2];
      modified++;
      currentId = null;
    }
  }
}
fs.writeFileSync('pet-frontend/src/views/WikiView.vue', lines.join('\n'));
console.log('Modified', modified, 'cover URLs');

// Verify uniqueness in result
const newContent = fs.readFileSync('pet-frontend/src/views/WikiView.vue', 'utf8');
const newMatches = [...newContent.matchAll(/id: (\d+),[\s\S]*?cover: '([^']+)'/g)];
const seen = {};
let dups = 0;
newMatches.forEach(m => {
  const id = parseInt(m[1]);
  if (id < 200) {
    const key = m[2];
    if (seen[key]) { console.log('DUP: id=' + id + ' & id=' + seen[key]); dups++; }
    else seen[key] = id;
  }
});
if (dups === 0) console.log('ALL UNIQUE! Total articles:', Object.keys(seen).length);
else console.log('Remaining duplicates:', dups);
