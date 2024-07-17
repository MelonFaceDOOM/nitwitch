// -------------------------------------------------------------------------
// SETTINGS/GLOBAL VARS
// -------------------------------------------------------------------------

    let adventureTitle = null;
    const HORIZONTAL_GAP = 2;
    const VERTICAL_GAP = 40;
    const BOX_WIDTH = 40;
    const BOX_HEIGHT = 25;
    const MAX_CHILDREN = 5;
    const MAX_TREE_DEPTH = 7;
    let CANVAS = null;
    let CTX = null;
    let IS_DRAGGING = false;
    let START_X, START_Y, OFFSET_X = 0, OFFSET_Y = 0;

    var globalRects = [];
    var globalLines = [];
    let nullCard = {
        cardId: null,
        cardText: "",
        selected: true,
        x: 0,
        y: 0,
        w: 0,
        h: 0,
        frondWidth: 0
    };
    var globalSelectedRect = nullCard;

    function loadCanvas() {
        CANVAS = document.getElementById('myCanvas');
        CTX = CANVAS.getContext('2d');
    }

    function collides(rects, x, y) {
        for (var i = 0, len = rects.length; i < len; i++) {
            var left = rects[i].x, right = rects[i].x+rects[i].w;
            var top = rects[i].y, bottom = rects[i].y+rects[i].h;
            if (right > x
                && left <= x
                && bottom > y
                && top <= y) {
                return rects[i];
            }
        }
        return false;
    }

    function addCanvasListeners() {
        // Mouse down event handler
        canvasContainer.addEventListener('mousedown', (event) => {
            var r = collides(globalRects, event.offsetX, event.offsetY);
            if (r !== false) {
                r.selected = !r.selected;
                if (r.selected === false) {
                    // click already-selected card to unselect
                    globalSelectedRect = nullCard;
                } else {
                    if (globalSelectedRect.cardId !== r.cardId) {
                        globalSelectedRect.selected = false;
                    }
                    globalSelectedRect = r;  // refers to the object in the list. not a copy.
                }
                redraw(globalRects, globalLines);
                updateHTMLInfo();
            } else {
                IS_DRAGGING = true;
                START_X = event.clientX;
                START_Y = event.clientY;
            }
        }, false);

        // Mouse move event handler
        canvasContainer.addEventListener('mousemove', (event) => {
            if (IS_DRAGGING) {
                updateCanvasPosition(event.clientX, event.clientY);
            }
        });

        // Mouse up event handler
        canvasContainer.addEventListener('mouseup', () => {
            IS_DRAGGING = false;
        });

        // Mouse leave event handler
        canvasContainer.addEventListener('mouseleave', () => {
            IS_DRAGGING = false;
        });
    }

// -------------------------------------------------------------------------
// ORCHESTRATE EVERYTHING
// -------------------------------------------------------------------------

    document.addEventListener('DOMContentLoaded', () => {
        const titleElement = document.getElementById('adventure-title');
        adventureTitle = titleElement.getAttribute('data-title');
        doStuff();
    });

    function doStuff() {
        loadCanvas();
        addCanvasListeners();
        fetchGameData(adventureTitle).then(data => {
            globalRects = loadGameData(data);
            globalRects = assignFrondWidths(globalRects);
            globalRects = assignXPosBasedOnFrondWidth(globalRects);
            globalRects = normalizeCoords(globalRects);
            // set canvas bounds and convert rect coords from top-left to bottom-left system
            drawRectsAndLines();
            centreCanvasOnRect(globalRects[0]);
            });
    }


// -------------------------------------------------------------------------
// PULL DATA FROM API
// -------------------------------------------------------------------------

    async function fetchGameData(title) {
        try {
            const response = await fetch(`/adventures/game_content/${title}`);
            if (!response.ok) {
                throw new Error('Network response was not ok');
            }
            data = await response.json();
            return data;
        } catch (error) {
            console.error('Error fetching adventure cards:', error);
        }
    }

    function loadGameData(data) {
        let rects = [];
        for (let i = 0; i < data.cards.length; i++) {
            card_data = data.cards[i];
            let rect = {
                cardId: card_data.card_id,
                cardText: card_data.card_text,
                cardOptions: [],
                selected: false,
                x: 0,
                y: BOX_HEIGHT * (card_data.card_id.length - 1) + VERTICAL_GAP * (card_data.card_id.length - 1),
                w: BOX_WIDTH,
                h: BOX_HEIGHT,
                frondWidth: 0
            };

            for (let j = 0; j < card_data.options.length; j++) {
                option_data = card_data.options[j]
                let option = {
                    optionText: option_data.option_text,
                    linkedCardId: option_data.linked_card_id
                };
                rect.cardOptions.push(option);
            }
            rects.push(rect);
        };
        return rects;
    }

// -------------------------------------------------------------------------
// UPDATE CANVAS AND HTML INFO
// -------------------------------------------------------------------------

    function drawRectsAndLines() {
        // set canvas bounds and convert rect coords from top-left to bottom-left system
        let boundingCoords = getRectsBounds(globalRects);
        CANVAS.width = boundingCoords.maxX - boundingCoords.minX;
        CANVAS.height = boundingCoords.maxY - boundingCoords.minY;
        // create lines
        globalLines = createLines(globalRects); // update global array
        // draw everything
        redraw(globalRects, globalLines);
    }

    function updateHTMLInfo() {
    // update values on web page that display info about the selected rect
        let divRectId = document.getElementById('selected-rect-id');
        if (globalSelectedRect.cardId === null) {
            divRectId.textContent = "";
        } else {
            divRectId.textContent = globalSelectedRect.cardId;
        }
//        let divRectCoords = document.getElementById('selected-rect-coords');
        let x = globalSelectedRect.x
        let y = globalSelectedRect.y
//        divRectCoords.textContent = `${x}, ${y}`;
        let divRectText = document.getElementById('selected-rect-text');
        let rectText = globalSelectedRect.cardText;
        divRectText.textContent = `${rectText} \n`;

        let divRectOptions = document.getElementById('selected-rect-options');
        divRectOptions.innerHTML = ''; // Clear any existing content

        // create a link element for each option
        if (globalSelectedRect.cardOptions && globalSelectedRect.cardOptions.length > 0) {
        globalSelectedRect.cardOptions.forEach(option => {
            let link = document.createElement('a');
            link.href = `/adventures/${adventureTitle}/${option.linkedCardId}`;
            link.textContent = option.optionText;
            link.classList.add('info-option-link');
            divRectOptions.appendChild(link);
        });
    }
    }
// -------------------------------------------------------------------------
// CANVAS CLICK AND DRAG STUFF
// -------------------------------------------------------------------------

   // this is the max area that can be drawn on.
   // commented out because it is going to be calculated later when rects are created
   // CANVAS.width = 1500;
   // CANVAS.height = 2000;

    // Update the canvas position based on mouse drag
    function updateCanvasPosition(x, y) {
        OFFSET_X += x - START_X;
        OFFSET_Y += y - START_Y;
        CANVAS.style.left = OFFSET_X + 'px';
        CANVAS.style.top = OFFSET_Y + 'px';
        START_X = x;
        START_Y = y;
    }

    function centreCanvasOnRect(rect) {
        START_X = 0;
        START_Y = 0;
        windowWidth = 800;
        windowHeight = 600; // todo pull this from something?
        xAdjustment =  Math.floor(windowWidth/2 - (rect.x + rect.w/2));
        yAdjustment = Math.floor(windowHeight - rect.y - rect.h);
        updateCanvasPosition(xAdjustment, yAdjustment);
    }

// -------------------------------------------------------------------------
// DRAW RECTANGLES ON CANVAS
// -------------------------------------------------------------------------

    function redraw(rects, lines) {
        CTX.clearRect(0, 0, CANVAS.width, CANVAS.height);
        for (let i = 0, len = rects.length; i < len; i++) {
            let r = rects[i];
            CTX.fillStyle = 'green';
            if (r.selected) {
                CTX.fillStyle = 'red';
            }
            CTX.fillRect(r.x, r.y, r.w, r.h);
        }
        CTX.strokeStyle = 'black';
        CTX.beginPath();
        for (let i = 0; i < lines.length; i++) {
            let line = lines[i];
            CTX.moveTo(line.x1, line.y1);
            CTX.lineTo(line.x2, line.y2);
        }
        CTX.stroke();
    }

// -------------------------------------------------------------------------
// CREATE CARDS (pre-rectangle step)
// -------------------------------------------------------------------------

    function getLowestLenCards(cards) {
        let minLength = Math.min(...cards.map(obj => obj.length));
        let lowestLenCards = cards.filter(card => card.length === minLength);
        let remainingCards = cards.filter(card => card.length !== minLength);
        return { lowestLenCards, remainingCards };
    }

    function createAllChildren(parent, maxChildren, maxDepth) {
        // this works with cards (i.e. strings like "0", "01", etc.), not rects
        let children = [];
        if (parent.length === maxDepth) {
            return children;
        }
        else {
            let numChildren = getRandomInt(maxChildren);
            for (let i = 0; i < numChildren; i++) {
                let child = parent + i.toString();
                children.push(child);
                let grandChildren = createAllChildren(child, maxChildren, maxDepth);
                children = children.concat(grandChildren);
            }
        }
        return children;
    }

    function getRandomInt(max) {
        return Math.floor(Math.random() * max);
    }


// -------------------------------------------------------------------------
// RECURSIVELY MEASURE WIDTH AND ASSIGN X POS
// -------------------------------------------------------------------------

    function getRectById(rects, cardId) {
        return rects.filter(rect => rect.cardId === cardId)[0]
    }

    function getRoots(rects) {
        let minLength = Math.min(...rects.map(obj => obj.cardId.length));
        let roots = rects.filter(rect => rect.cardId.length === minLength);
        return roots;
    }

    function isLeaf(rects, rect) {
        children = getChildren(rects, rect)
        if (children.length > 0) {
            return false;
        } else {
            return true;
        }
    }

    function calcFrondWidth(rects, rect) {
    // assumes children frondWidth has already been calculated
    // i.e. this should be called on the tree starting from the top then moving down
        if (isLeaf(rects, rect)) {
            return rect.w;
        } else {
            let frondWidth = 0;
            let children = getChildren(rects, rect);
            for (let i = 0; i < children.length; i++) {
                const child = children[i];
                frondWidth += child.frondWidth;
            }
            const totalGapSize = HORIZONTAL_GAP * (children.length - 1);
            frondWidth += totalGapSize;
            if (frondWidth > rect.w) {
                return frondWidth;
            } else {
                return rect.w;
            }
        }
    }

    function assignFrondWidths(rects) {
        let rectsWithWidth = rects.slice();
        let maxLength = Math.max(...rectsWithWidth.map(obj => obj.cardId.length));
        for (let i = maxLength; i >= 1; i--) {
            let rowRects = rectsWithWidth.filter(rect => rect.cardId.length === i);
            for (let j = 0; j < rowRects.length; j++) {
                let rect = rowRects[j];
                rect.frondWidth = calcFrondWidth(rectsWithWidth, rect);
                rectsWithWidth = removeRectsFromArrayByID(rectsWithWidth, [rect]);
                rectsWithWidth.push(rect);
            }
        }
        return rectsWithWidth;
    }

    function assignXPosBasedOnFrondWidth(rects) {
        // todo: does this alter the rect in the original array by changing root.x
        let rectsWithXPos = [];
        let root = getRectById(rects, "0");
        root.x = Math.ceil(root.frondWidth/2);
        rectsWithXPos.push(root);
        let childrenWithXPos = assignXPosForAllChildren(rects, root);
        rectsWithXPos = rectsWithXPos.concat(childrenWithXPos);
        return rectsWithXPos;
    }

    function assignXPosForAllChildren(rects, rect) {
        let rectsWithXPos = [];
        let children = getChildren(rects, rect);
        if (children.length === 0) {
            return [];
        }
        let startX = rect.x - Math.ceil(rect.frondWidth/2) - HORIZONTAL_GAP; // - horizontal_gap so that we can add it to each child and neutralize its effect on the first one
        for (let i = 0; i < children.length; i++) {
            child = children[i];
            child.x = startX + Math.ceil(child.frondWidth/2) + HORIZONTAL_GAP;
            startX = child.x + Math.ceil(child.frondWidth/2);
            rectsWithXPos.push(child);
            let grandchildrenWithXPos = assignXPosForAllChildren(rects, child);
            rectsWithXPos = rectsWithXPos.concat(grandchildrenWithXPos);
        }
        return rectsWithXPos;
    }

// -------------------------------------------------------------------------
// FUNCS FROM OTHER FILE THAT I ALSO USED HERE
// -------------------------------------------------------------------------

    function getChildren(rects, parent) {
        return rects.filter(rect =>
            rect.cardId.length === parent.cardId.length + 1 &&
            rect.cardId.startsWith(parent.cardId)
        );
    }

    function removeRectsFromArrayByID(rects, rects_to_remove) {
        let filteredIds = rects_to_remove.map(item => item.cardId);
        return rects.filter(item => !filteredIds.includes(item.cardId));
    }

// -------------------------------------------------------------------------
// CONVERT BOTTOM-LEFT RECTANGLE COORDS TO TOP-LEFT COORDS USED BY CANVAS
// -------------------------------------------------------------------------

    function getRectsBounds(rects) {
        let minY = Number.MAX_SAFE_INTEGER;
        let maxY = Number.MIN_SAFE_INTEGER;
        let minX = Number.MAX_SAFE_INTEGER;
        let maxX = Number.MIN_SAFE_INTEGER;

        rects.forEach(rect => {
            minY = Math.min(minY, rect.y);
            maxY = Math.max(maxY, rect.y + rect.h);
            minX = Math.min(minX, rect.x);
            maxX = Math.max(maxX, rect.x + rect.w);
        });

        return { minY, maxY, minX, maxX };
    }

    function normalizeCoords(rects) {
        let boundingCoords = getRectsBounds(rects);
        let xAdjustment = 0 - boundingCoords.minX;
        let height = boundingCoords.maxY - boundingCoords.minY;
        let normalizedRects = [];
        for (let i = 0; i < rects.length; i++) {
            r = rects[i];
            let yNorm = height - r.h - r.y;
            let xNorm = xAdjustment + r.x;
            r.x = xNorm;
            r.y = yNorm;
            normalizedRects.push(r);
        }
        return normalizedRects;
    }

// -------------------------------------------------------------------------
// DRAW LINES FROM PARENTS TO CHILDREN
// -------------------------------------------------------------------------

    function createLines(rects) {
        var lines = [];
        for (var i = 0; i < rects.length; i++) {
            var parent = rects[i];
            var children = getChildren(rects, parent);
            for (var j = 0; j < children.length; j++) {
                var child = children[j];
                lines.push({
                    x1: parent.x + parent.w / 2,
                    y1: parent.y,
                    x2: child.x + child.w / 2,
                    y2: child.y + parent.h
                });
            }
        }
        return lines;
    }