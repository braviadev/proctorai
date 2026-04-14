/*
# Clean UI programming in a vacuum

This app was written for Chapter 19 in the 3rd edition of Eloquent
JavaScript—it aims to demonstrate modern UI programming without
depending on a specific framework or library.

Its convention is that components have an interface like this:

```
{
  constructor(state: Object, dispatch: fn(Object))
  dom: Node,
  setState(state: Object)
}
```

Leaf components may replace `dispatch` with another type of value or
set of options (for example callbacks).

The constructor creates the DOM for the component, and attaches event
handlers that may call `dispatch` to initiate an application state
update. At the top level of the app, a state update function computes
a new state from the old state and the value given to `dispatch`, and
calls `setState` on the top-level component with that new state.

Components' `setState` method updates their DOM to reflect the current
state, and recursively calls `setState` on any child components.

Defining such components manually is more work than doing so in a
modern framework, but isn't _too_ awful, and enough for a simple app
like this.
*/

class Picture {
  constructor(width, height, pixels) {
    this.width = width;
    this.height = height;
    this.pixels = pixels;
  }
  static empty(width, height, color) {
    let pixels = new Array(width * height).fill(color);
    return new Picture(width, height, pixels);
  }
  pixel(x, y) {
    return this.pixels[x + y * this.width];
  }
  setPixel(x, y, color) {
    this.pixels[x + y * this.width] = color;
  }
  copy() {
    return new Picture(this.width, this.height, this.pixels.slice());
  }
}

function addChildren(dom, children) {
  for (let child of children) {
    if (typeof child == "string") {
      child = document.createTextNode(child);
    }
    dom.appendChild(child);
  }
  return dom;
}

function elt(type, attrs, ...children) {
  let dom = document.createElement(type);
  if (attrs) {
    for (let [name, value] of Object.entries(attrs)) {
      if (typeof value == "function") dom[name] = value;
      else dom.setAttribute(name, value);
    }
  }
  return addChildren(dom, children);
}

function frag(...children) {
  return addChildren(document.createDocumentFragment(),
                     children);
}

const scale = 10;

function mousePosition(event, rect) {
  return {x: Math.floor((event.clientX - rect.left) / scale),
          y: Math.floor((event.clientY - rect.top) / scale)};
}

class PictureCanvas {
  constructor(picture, mouseDown) {
    this.dom = elt("canvas", {
      onmousedown: event => this.mouseDown(event, mouseDown)
    });
    drawPicture(picture, this.dom, scale);
  }

  mouseDown(downEvent, onMouseDown) {
    let rect = this.dom.getBoundingClientRect();
    let pos = mousePosition(downEvent, rect);
    let onMove = onMouseDown(pos);
    if (!onMove) return;
    let move = moveEvent => {
      if (moveEvent.buttons == 0) {
        this.dom.removeEventListener("mousemove", move);
      } else {
        let newPos = mousePosition(moveEvent, rect);
        if (newPos.x == pos.x && newPos.y == pos.y) return;
        pos = newPos;
        onMove(newPos);
      }
    };
    this.dom.addEventListener("mousemove", move);
  }

  setState(picture) {
    if (this.picture == picture) return;
    this.picture = picture;
    drawPicture(this.picture, this.dom, scale);
  }
}

function drawPicture(picture, canvas, scale) {
  canvas.width = picture.width * scale;
  canvas.height = picture.height * scale;
  let cx = canvas.getContext("2d");

  for (let y = 0; y < picture.height; y++) {
    for (let x = 0; x < picture.width; x++) {
      cx.fillStyle = picture.pixel(x, y);
      cx.fillRect(x * scale, y * scale, scale, scale);
    }
  }
}

class PixelEditor {
  constructor(state, dispatch) {
    this.state = state;

    this.canvas = new PictureCanvas(state.picture, pos => {
      let onMove = tools[this.state.tool](pos, this.state, dispatch);
      return onMove && (pos => onMove(pos, this.state, dispatch));
    });
                                    
    this.controls = controls
      .map(Control => new Control(state, dispatch));
    this.dom = frag(this.canvas.dom, elt("br"),
                    ...this.controls.reduce((a, c) => a.concat(" ", c.dom), []));
  }

  setState(state) {
    this.state = state;
    this.canvas.setState(state.picture);
    for (let c of this.controls) c.setState(state);
  }
}

let controls = [];

controls.push(class ToolSelect {
  constructor(state, dispatch) {
    this.select = elt("select", {
      onchange: () => dispatch({tool: this.select.value})
    }, ...Object.keys(tools).map(n => elt("option", {}, n)));
    this.select.value = state.tool;
    this.dom = frag("🖌 Tool: ", this.select);
  }
  setState(state) { this.select.value = state.tool; }
});

controls.push(class ColorSelect {
  constructor(state, dispatch) {
    this.input = elt("input", {
      type: "color",
      value: state.color,
      onchange: () => dispatch({color: this.input.value})
    });
    this.dom = frag("🎨 Color: ", this.input);
  }
  setState(state) { this.input.value = state.color; }
});

controls.push(class SaveButton {
  constructor(_, state) {
    this.state = state;
    this.dom = elt("button", {
      onclick: () => this.save()
    }, "💾 Save");
  }
  save() {
    let canvas = elt("canvas");
    drawPicture(this.state.picture, canvas, 1);
    let link = elt("a", {
      href: canvas.toDataURL(),
      download: "pixelart.png"
    });
    document.body.appendChild(link);
    link.click();
    link.remove();
  }
  setState(state) { this.state = state; }
});

function pictureFromImage(image) {
  let width = Math.min(100, image.width);
  let height = Math.min(100, image.height);
  let canvas = elt("canvas", {width, height});
  let cx = canvas.getContext("2d");
  cx.drawImage(image, 0, 0);
  let pixels = [];
  let {data} = cx.getImageData(0, 0, width, height);

  function hex(n) {
    let h = n.toString(16);
    return h.length == 1 ? "0" + h : h;
  }
  for (let i = 0; i < data.length; i += 4) {
    let [r, g, b] = data.slice(i, i + 3);
    pixels.push("#" + hex(r) + hex(g) + hex(b));
  }
  return new Picture(width, height, pixels);
}

controls.push(class LoadButton {
  constructor(_, dispatch) {
    this.dom = elt("button", {
      onclick: () => this.load(dispatch)
    }, "📁 Load");
  }
  load(dispatch) {
    let input = elt("input", {type: "file"});
    document.body.appendChild(input);
    input.onchange = () => {
      if (!input.files.length) return;
      let reader = new FileReader();
      reader.addEventListener("load", () => {
        let image = elt("img", {
          onload: () =>
            dispatch({picture: pictureFromImage(image)}),
          src: reader.result
        });
      });
      reader.readAsDataURL(input.files[0]);
    };
    input.click();
    input.remove();
  }
  setState(_) {}
});

let tools = {};

tools.draw = (pos, state, dispatch) => {
  function drawDot(pos, state) {
    let picture = state.picture.copy();
    picture.setPixel(pos.x, pos.y, state.color);
    dispatch({picture});
  }
  drawDot(pos, state);
  return drawDot;
};

tools.rectangle = (start, state, dispatch) => {
  function drawRect(pos) {
    let xStart = Math.min(start.x, pos.x);
    let xEnd = Math.max(start.x, pos.x);
    let yStart = Math.min(start.y, pos.y);
    let yEnd = Math.max(start.y, pos.y);
    let picture = state.picture.copy();
    for (let y = yStart; y <= yEnd; y++) {
      for (let x = xStart; x <= xEnd; x++) {
        picture.setPixel(x, y, state.color);
      }
    }
    dispatch({picture});
  }
  drawRect(start);
  return drawRect;
};

const around = [{dx: -1, dy: 0}, {dx: 1, dy: 0},
                {dx: 0, dy: -1}, {dx: 0, dy: 1}];

tools.fill = (pos, state, dispatch) => {
  let targetColor = state.picture.pixel(pos.x, pos.y);
  if (targetColor == state.color) return;
  let picture = state.picture.copy();
  let todo = [pos];
  while (todo.length) {
    let pos = todo.pop();
    picture.setPixel(pos.x, pos.y, state.color);
    for (let {dx, dy} of around) {
      let x = pos.x + dx, y = pos.y + dy;
      if (x >= 0 && x < picture.width &&
          y >= 0 && y < picture.height &&
          picture.pixel(x, y) == targetColor) {
        todo.push({x, y});
      }
    }
  }
  dispatch({picture});
};

tools.pick = (pos, state, dispatch) => {
  dispatch({color: state.picture.pixel(pos.x, pos.y)});
};

controls.push(class UndoButton {
  constructor(state, dispatch) {
    this.dom = elt("button", {
      onclick: () => dispatch({history: "undo"}),
      disabled: state.undo == null
    }, "⮪ Undo");
  }
  setState(state) { this.dom.disabled = state.undo == null }
});

controls.push(class RedoButton {
  constructor(state, dispatch) {
    this.dom = elt("button", {
      onclick: () => dispatch({history: "redo"}),
      disabled: state.redo == null
    }, "⮫ Redo");
  }
  setState(state) { this.dom.disabled = state.redo == null }
});

function historyDispatch(state, action) {
  let time = Date.now();
  if (action.history == "undo") {
    return Object.assign({}, state, {
      picture: state.undo.picture,
      undo: state.undo.prev,
      redo: {picture: state.picture, prev: state.redo, time}
    });
  } else if (action.history == "redo") {
    return Object.assign({}, state, {
      picture: state.redo.picture,
      undo: {picture: state.picture, prev: state.undo, time},
      redo: state.redo.prev,
    });
  } else {
    let undo = state.undo;
    if (action.picture && (!undo || undo.time < time - 2000)) {
      undo = {picture: state.picture, time, prev: undo};
    }
    return Object.assign({}, state, action, {redo: null, undo});
  }
}

let state = {
  picture: Picture.empty(80, 30, "#eeeeee"),
  tool: "draw",
  color: "#000000"
};
let app = window.app = new PixelEditor(state, action => {
  state = historyDispatch(state, action);
  app.setState(state);
});
document.body.appendChild(app.dom);