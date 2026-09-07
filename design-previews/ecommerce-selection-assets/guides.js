(function () {
  'use strict';

  const ink = '#8b9086';
  const accent = '#4d6537';
  const skin = '#e5e3dc';
  const scarf = '#ecddd4';
  const top = '#dce8ec';

  const frame = '<rect width="320" height="380" rx="10" fill="#f0eee7"/>' +
    '<path d="M46 28H28V46M274 28H292V46M28 334V352H46M274 352H292V334" fill="none" stroke="#b8bdb2" stroke-width="1.5"/>' +
    '<path d="M153 28H167M153 352H167M28 183V197M292 183V197" fill="none" stroke="#c8cbc1" stroke-width="1"/>';

  function path(d, fill, stroke, extra) {
    return '<path d="' + d + '" fill="' + (fill || 'none') + '" stroke="' + (stroke || ink) + '" stroke-width="1.65" stroke-linecap="round" stroke-linejoin="round"' + (extra || '') + '/>';
  }

  function turnCue(reverse) {
    return '<g transform="translate(' + (reverse ? '278 0' : '0 0') + ') scale(' + (reverse ? '-1' : '1') + ' 1)">' +
      path('M242 143C263 155 267 181 255 202', 'none', accent) +
      path('M255 202L254 191M255 202L266 198', 'none', accent) + '</g>';
  }

  function heightCue() {
    return path('M264 69V309M259 75L264 69L269 75M259 303L264 309L269 303', 'none', accent) +
      path('M253 69H269M253 309H269', 'none', '#c1c8b7');
  }

  function scarfArranged(reverse) {
    return path('M119 89C145 78 183 83 195 101C206 117 199 141 181 158L128 208C119 217 121 230 135 239L209 285L184 323L110 276C78 256 79 226 103 202L154 151C170 136 178 121 165 115C151 109 135 113 126 123Z', scarf) +
      path('M130 106C147 100 172 102 179 114C187 127 176 145 163 157L116 204C95 225 95 245 118 261L197 310', 'none', '#b9ada4') +
      path('M119 89L126 123M184 323L209 285', 'none', ink) +
      (reverse ? path('M140 128C161 122 169 128 161 140M125 229L187 272', 'none', '#b6aaa1', ' stroke-dasharray="4 6"') + turnCue(true) :
        path('M91 129C74 154 73 174 83 191M83 191L73 186M83 191L86 180', 'none', accent));
  }

  function scarfWorn() {
    return path('M126 29L128 71C130 88 143 101 160 104C177 101 190 88 192 71L194 29', skin) +
      path('M141 98L139 127C125 135 101 139 83 149C65 160 56 184 52 217L48 337H272L268 217C264 184 255 160 237 149C219 139 195 135 181 127L179 98', skin) +
      path('M85 180L91 260M235 180L229 260', 'none', '#b5b7ad') +
      path('M131 123C138 119 148 126 160 130C174 132 182 119 190 126L199 151C185 174 137 173 123 151Z', scarf) +
      path('M135 161L157 171L143 303L110 299Z', scarf) +
      path('M164 168L188 160L209 279L178 286Z', scarf) +
      path('M134 139C149 151 174 156 190 140M135 178L122 284M180 178L194 269', 'none', '#b9ada4') +
      path('M228 116C240 122 246 132 246 144M246 144L239 137M246 144L253 137', 'none', accent);
  }

  function flatTop(back) {
    return path('M111 108L80 122L47 178L82 199L101 176L102 290Q160 300 218 290L219 176L238 199L273 178L240 122L209 108L184 96H136Z', top) +
      path(back ? 'M136 96Q160 114 184 96' : 'M136 96Q140 130 160 133Q180 130 184 96', 'none', ink) +
      path('M80 122L101 176M240 122L219 176M103 279Q160 289 217 279', 'none', '#b2c2c6') +
      (back ? turnCue(true) : turnCue(false));
  }

  function mannequin() {
    return path('M145 59V86L126 103M175 59V86L194 103', '#faf9f4', '#b5b9af', ' stroke-dasharray="5 5"') +
      path('M112 102L81 118L57 169L85 185L103 158L106 284Q160 300 214 284L217 158L235 185L263 169L239 118L208 102L183 89H137Z', top) +
      path('M137 89Q140 120 160 123Q180 120 183 89', '#f0eee7') +
      path('M104 164Q119 207 106 268M216 164Q201 207 214 268M115 278Q160 289 205 278', 'none', '#b2c2c6') +
      path('M148 301V319M172 301V319M141 326H179', 'none', '#b5b9af', ' stroke-dasharray="4 5"') +
      path('M72 240H91M85 234L91 240L85 246M248 240H229M235 234L229 240L235 246', 'none', accent);
  }

  function foldedTop() {
    return path('M111 112L87 132L76 185L105 196L104 288Q159 296 216 288L215 196L244 185L233 132L209 112L185 101H135Z', '#e6eef0') +
      path('M113 113L132 102Q140 124 160 124Q180 124 188 102L207 113L213 291Q160 299 107 291Z', top) +
      path('M132 102Q135 143 160 146Q185 143 188 102M111 259Q161 266 209 259', 'none', '#b2c2c6') +
      path('M60 213C74 231 91 234 108 227M108 227L99 224M108 227L105 237M260 213C246 231 229 234 212 227M212 227L221 224M212 227L215 237', 'none', accent);
  }

  function wornTop(back) {
    return path('M128 28L130 68Q137 92 160 98Q183 92 190 68L192 28', skin) +
      path('M143 94L141 117L102 133C80 144 70 170 64 207L49 307Q47 320 56 323Q67 325 72 311L94 229L102 203L101 339H219L218 203L226 229L248 311Q253 325 264 323Q273 320 271 307L256 207C250 170 240 144 218 133L179 117L177 94', skin) +
      path('M141 117L103 130L80 178L105 196L118 176L113 281Q160 289 207 281L202 176L215 196L240 178L217 130L179 117Z', top) +
      path(back ? 'M141 117Q160 131 179 117' : 'M141 117Q143 145 160 148Q177 145 179 117', 'none', ink) +
      path('M119 191L120 254M201 191L200 254M114 272Q160 280 206 272', 'none', '#b2c2c6') +
      path('M158 288V339', 'none', '#b7b9af') +
      (back ? turnCue(true) : path('M70 107H93M87 101L93 107L87 113', 'none', accent));
  }

  function sideWornTop() {
    return path('M134 28L135 64Q144 91 163 96Q182 84 188 62L190 28', skin) +
      path('M150 94L147 117C127 125 113 134 104 153L99 207L91 303Q90 316 99 319Q110 321 113 307L130 226L137 195L127 339H208L198 219C214 187 223 151 204 133L174 116L173 94', skin) +
      path('M147 116L123 128L112 174L139 185L143 168L137 280Q169 291 207 278L198 205L214 160L200 130L174 116Z', top) +
      path('M147 116Q159 135 174 116M176 159C169 181 163 220 167 259M139 270Q172 282 205 268', 'none', '#b2c2c6') +
      path('M190 161L187 223L201 307Q204 321 213 319Q223 316 221 304L215 219L214 160', skin) +
      path('M176 289L170 339', 'none', '#b7b9af') + turnCue(false);
  }

  function fullBody() {
    return path('M142 28L143 47L137 58L109 70C97 78 92 92 88 119L77 183Q75 196 83 199Q93 200 96 188L112 141L116 122L123 194L117 252L112 318L103 333Q100 341 111 342H134L144 316L155 247L161 220L168 247L178 316L184 342H207Q219 341 216 333L207 318L201 252L195 194L202 122L207 141L223 188Q226 200 236 199Q244 196 242 183L231 119C227 92 222 78 210 70L181 58L176 47L177 28', skin) +
      path('M137 58L111 69L94 105L115 116L124 101L124 184Q160 193 196 184L196 101L205 116L226 105L209 69L181 58Z', top) +
      path('M137 58Q143 80 159 82Q175 80 181 58M125 176Q160 185 195 176', 'none', '#b2c2c6') +
      path('M125 191L160 197L195 191M160 197L161 220M114 316L137 318M180 318L205 316', 'none', '#b5b8ae') + heightCue();
  }

  const diagrams = {
    scarf: { arranged: () => scarfArranged(false), reverse: () => scarfArranged(true), worn: scarfWorn },
    top: { back: () => flatTop(true), mannequin, folded: foldedTop, 'front-worn': () => wornTop(false), 'back-worn': () => wornTop(true), 'side-worn': sideWornTop, 'full-body': fullBody },
  };

  window.renderCompositionGuide = function (kind, view) {
    const render = diagrams[kind] && diagrams[kind][view];
    if (typeof render !== 'function') return '';
    return '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 320 380" preserveAspectRatio="xMidYMid meet" aria-hidden="true" focusable="false">' + frame + render() + '</svg>';
  };
}());
