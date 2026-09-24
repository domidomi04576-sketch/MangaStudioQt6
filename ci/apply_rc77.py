from pathlib import Path
import sys

root = Path(sys.argv[1] if len(sys.argv) > 1 else 'work/source')

def edit(rel, transforms):
    p = root / rel
    s = p.read_text(encoding='utf-8')
    for label, old, new in transforms:
        if old not in s:
            raise SystemExit(f'{rel}: target not found: {label}')
        s = s.replace(old, new, 1)
    p.write_text(s, encoding='utf-8', newline='\n')

edit('src/ui/node.h', [
('breakout resize state',
'''    qreal fontSize = 0;
    QPointF cropOffset;
  };''',
'''    qreal fontSize = 0;
    QPointF cropOffset;
    bool breakout = false;
  };'''),
('owned breakout helpers',
'''  QPainterPath ellipseBody() const {
    QPainterPath p;
    p.addEllipse(box().adjusted(3, 3, -3, -3));
    return p;
  }
''',
'''  QPainterPath ellipseBody() const {
    QPainterPath p;
    p.addEllipse(box().adjusted(3, 3, -3, -3));
    return p;
  }
  QPainterPath bubbleBodyPath() const {
    QPainterPath path;
    if (kind != "bubble")
      return silhouette();
    if (style == "ナレーション") {
      path.addRect(box().adjusted(3, 3, -3, -3));
      return path;
    }
    if (style == "絶叫" || style == "怒り") {
      QPolygonF poly;
      for (int i = 0; i < 40; i++) {
        qreal a = i * 2 * M_PI / 40, r = i % 2 ? .8 : 1.;
        poly << QPointF(size.width() / 2 +
                            std::cos(a) * size.width() / 2 * r,
                        size.height() / 2 +
                            std::sin(a) * size.height() / 2 * r);
      }
      path.addPolygon(poly);
      path.closeSubpath();
      return path;
    }
    return ellipseBody();
  }
  QList<Node *> ownedBreakouts() const {
    QList<Node *> result;
    if (kind != "panel" || !scene())
      return result;
    for (auto *item : scene()->items(Qt::AscendingOrder))
      if (auto *n = dynamic_cast<Node *>(item);
          n && n != this && !n->parentItem() &&
          n->metadata.value("breakout").toBool() &&
          n->metadata.value("ownerPanelId").toString() == id)
        result << n;
    return result;
  }
  void capturePanelResizeFollowers() {
    pressChildren.clear();
    if (kind != "panel")
      return;
    for (auto *c : childItems())
      if (auto *n = dynamic_cast<Node *>(c))
        pressChildren.append({n, n->pos(), n->size, n->fontSize,
                              n->cropOffset, false});
    for (auto *n : ownedBreakouts())
      pressChildren.append({n, mapFromScene(n->mapToScene(QPointF())), n->size,
                            n->fontSize, n->cropOffset, true});
  }
  void scalePanelResizeFollowers(qreal sx, qreal sy) {
    if (kind != "panel")
      return;
    qreal sf = std::sqrt(qMax(0.0001, sx * sy));
    for (const auto &state : pressChildren) {
      if (!state.node)
        continue;
      if (state.breakout) {
        if (state.node->parentItem() ||
            !state.node->metadata.value("breakout").toBool() ||
            state.node->metadata.value("ownerPanelId").toString() != id)
          continue;
        state.node->setPos(
            mapToScene({state.pos.x() * sx, state.pos.y() * sy}));
      } else {
        if (state.node->parentItem() != this)
          continue;
        state.node->setPos(state.pos.x() * sx, state.pos.y() * sy);
      }
      state.node->resizeTo({qMax(1.0, state.size.width() * sx),
                            qMax(1.0, state.size.height() * sy)});
      state.node->cropOffset = {state.cropOffset.x() * sx,
                                state.cropOffset.y() * sy};
      if (state.node->kind == "bubble" || state.node->kind == "text" ||
          state.node->kind == "sfx" || state.node->kind == "mark")
        state.node->fontSize = qMax(5.0, state.fontSize * sf);
      state.node->update();
    }
  }
  void restorePanelResizeFollowers() {
    if (kind != "panel")
      return;
    for (const auto &state : pressChildren) {
      if (!state.node)
        continue;
      if (state.breakout) {
        if (state.node->parentItem() ||
            state.node->metadata.value("ownerPanelId").toString() != id)
          continue;
        state.node->setPos(mapToScene(state.pos));
      } else {
        if (state.node->parentItem() != this)
          continue;
        state.node->setPos(state.pos);
      }
      state.node->resizeTo(state.size);
      state.node->fontSize = state.fontSize;
      state.node->cropOffset = state.cropOffset;
      state.node->update();
    }
  }
'''),
('capture panel followers',
'''    pressChildren.clear();
    if (kind == "panel" && handle >= 0)
      for (auto *c : childItems())
        if (auto *n = dynamic_cast<Node *>(c))
          pressChildren.append({n, n->pos(), n->size, n->fontSize,
                                n->cropOffset});''',
'''    pressChildren.clear();
    if (kind == "panel" && handle >= 0)
      capturePanelResizeFollowers();'''),
('scale panel followers',
'''      if (kind == "panel" && !pressChildren.isEmpty()) {
        qreal sx = w / qMax(1.0, pressSize.width());
        qreal sy = h / qMax(1.0, pressSize.height());
        qreal sf = std::sqrt(qMax(0.0001, sx * sy));
        for (auto state : pressChildren)
          if (state.node && state.node->parentItem() == this) {
            state.node->setPos(state.pos.x() * sx, state.pos.y() * sy);
            state.node->resizeTo({qMax(1.0, state.size.width() * sx),
                                  qMax(1.0, state.size.height() * sy)});
            state.node->cropOffset = {state.cropOffset.x() * sx,
                                      state.cropOffset.y() * sy};
            if (state.node->kind == "bubble" || state.node->kind == "text" ||
                state.node->kind == "sfx" || state.node->kind == "mark")
              state.node->fontSize = qMax(5.0, state.fontSize * sf);
          }
      }''',
'''      if (kind == "panel" && !pressChildren.isEmpty()) {
        qreal sx = w / qMax(1.0, pressSize.width());
        qreal sy = h / qMax(1.0, pressSize.height());
        scalePanelResizeFollowers(sx, sy);
      }''')])

edit('src/ui/canvas.h', [
('frame occlusion helper',
'''class PageScene final : public QGraphicsScene {
public:
  void drawForeground(QPainter *p, const QRectF &exposed) override {''',
'''class PageScene final : public QGraphicsScene {
public:
  QPainterPath visiblePanelFrame(Node *panel) const {
    QPainterPath visible;
    if (!panel || panel->kind != "panel" || panel->border <= 0)
      return visible;
    QPainterPathStroker frameStroker;
    frameStroker.setWidth(panel->border);
    visible = frameStroker.createStroke(panel->silhouette());
    for (auto *n : panel->ownedBreakouts()) {
      if (!n->isVisible() || n->kind != "bubble")
        continue;
      auto body = panel->mapFromItem(n, n->bubbleBodyPath());
      QPainterPathStroker clearance;
      clearance.setWidth(qMax(2.0, panel->border + 2.0));
      auto occlusion = body.united(clearance.createStroke(body));
      visible = visible.subtracted(occlusion);
    }
    return visible;
  }
  void drawForeground(QPainter *p, const QRectF &exposed) override {'''),
('foreground frame respects breakout',
'''          p->setBrush(Qt::NoBrush);
          p->setPen(QPen(n->ink, n->border));
          p->drawPath(n->silhouette());''',
'''          p->setPen(Qt::NoPen);
          p->setBrush(n->ink);
          p->drawPath(visiblePanelFrame(n));'''),
('cancel breakout resize restore',
'''      if (resizing->kind == "panel") {
        for (const auto &state : resizing->pressChildren)
          if (state.node && state.node->parentItem() == resizing) {
            state.node->setPos(state.pos);
            state.node->resizeTo(state.size);
            state.node->fontSize = state.fontSize;
            state.node->cropOffset = state.cropOffset;
            state.node->update();
          }
      }
      resizing->pressChildren.clear();''',
'''      if (resizing->kind == "panel")
        resizing->restorePanelResizeFollowers();
      resizing->pressChildren.clear();'''),
('panel drag moves breakout owners',
'''        if (!panel->isLocked())
          for (auto *i : scene()->selectedItems())
            if (auto *n = dynamic_cast<Node *>(i);
                n && n->kind == "panel" && !n->isLocked())
              moving.append({n, n->pos()});''',
'''        if (!panel->isLocked()) {
          auto remember = [&](Node *node) {
            if (!node || node->isLocked())
              return;
            for (const auto &entry : moving)
              if (entry.first == node)
                return;
            moving.append({node, node->pos()});
          };
          for (auto *i : scene()->selectedItems())
            if (auto *n = dynamic_cast<Node *>(i);
                n && n->kind == "panel" && !n->isLocked()) {
              remember(n);
              for (auto *follower : n->ownedBreakouts())
                remember(follower);
            }
        }''')])

edit('src/ui/studio.h', [
('property resize follows owned breakouts',
'''      QSizeF beforeSize = n->size;
      struct PropertyChildState { Node *node; QPointF pos; QSizeF size; qreal font; QPointF crop; };
      QList<PropertyChildState> propertyChildren;
      if (n->kind == "panel")
        for (auto *c : n->childItems())
          if (auto *child = dynamic_cast<Node *>(c))
            propertyChildren.append({child, child->pos(), child->size, child->fontSize, child->cropOffset});
      n->resizeTo({w.value(), h.value()});
      if (n->kind == "panel" && beforeSize.width() > 0 && beforeSize.height() > 0 &&
          n->size != beforeSize) {
        qreal sx = n->size.width() / beforeSize.width();
        qreal sy = n->size.height() / beforeSize.height();
        qreal sf = std::sqrt(qMax(0.0001, sx * sy));
        for (auto state : propertyChildren) {
          state.node->setPos(state.pos.x() * sx, state.pos.y() * sy);
          state.node->resizeTo({qMax(1.0, state.size.width() * sx),
                                qMax(1.0, state.size.height() * sy)});
          state.node->cropOffset = {state.crop.x() * sx, state.crop.y() * sy};
          if (state.node->kind == "bubble" || state.node->kind == "text" ||
              state.node->kind == "sfx" || state.node->kind == "mark")
            state.node->fontSize = qMax(5.0, state.font * sf);
        }
      }''',
'''      QSizeF beforeSize = n->size;
      if (n->kind == "panel")
        n->capturePanelResizeFollowers();
      n->resizeTo({w.value(), h.value()});
      if (n->kind == "panel" && beforeSize.width() > 0 && beforeSize.height() > 0 &&
          n->size != beforeSize) {
        qreal sx = n->size.width() / beforeSize.width();
        qreal sy = n->size.height() / beforeSize.height();
        n->scalePanelResizeFollowers(sx, sy);
      }
      if (n->kind == "panel")
        n->pressChildren.clear();''')])

edit('src/version.h', [
('build number', '#define AMS_VERSION_BUILD 76', '#define AMS_VERSION_BUILD 77'),
('file version', '#define AMS_FILE_VERSION_STR "23.6.0.76"', '#define AMS_FILE_VERSION_STR "23.6.0.77"'),
('app version', '#define AMS_APP_VERSION_STR "23.6-RC7.6"', '#define AMS_APP_VERSION_STR "23.6-RC7.7"'),
('display version', '#define AMS_DISPLAY_VERSION_STR "23.6 RC7.6"', '#define AMS_DISPLAY_VERSION_STR "23.6 RC7.7"')])

reg = root / 'tests/regression.h'
s = reg.read_text(encoding='utf-8')
needle = '''  check("free layer saves and loads",
        w.writeFile(out + "/breakout.manga.json", err) &&
            w.readFile(out + "/breakout.manga.json", err) &&
            w.snapshot() == breakoutState);

'''
addition = '''  check("free layer saves and loads",
        w.writeFile(out + "/breakout.manga.json", err) &&
            w.readFile(out + "/breakout.manga.json", err) &&
            w.snapshot() == breakoutState);

  // Breakout speech stays owned by its panel for panel transforms, but is
  // rendered above the panel frame. Image-only transforms must never move it.
  w.restore(QJsonDocument::fromJson(before).object());
  p = w.panels().first();
  w.placeAsset({{"kind", "bubble"}, {"style", "通常"}},
               p->mapToScene({20, 180}));
  auto *breakoutBubble = w.selected().isEmpty() ? nullptr : w.selected().first();
  if (breakoutBubble) {
    breakoutBubble->size = {220, 160};
    breakoutBubble->setPos(-70, 120);
  }
  w.breakOutSelected();
  check("breakout bubble retains owner panel",
        breakoutBubble && !breakoutBubble->parentItem() &&
            breakoutBubble->metadata.value("breakout").toBool() &&
            breakoutBubble->metadata.value("ownerPanelId").toString() == p->id);
  if (breakoutBubble) {
    auto bodyInPanel =
        p->mapFromItem(breakoutBubble, breakoutBubble->bubbleBodyPath());
    auto visibleFrame = w.scene.visiblePanelFrame(p);
    check("breakout bubble occludes panel frame",
          visibleFrame.intersected(bodyInPanel).isEmpty());

    auto ownerLocalBefore =
        p->mapFromScene(breakoutBubble->mapToScene(QPointF()));
    auto bubbleSizeBefore = breakoutBubble->size;
    auto bubbleFontBefore = breakoutBubble->fontSize;
    auto panelSizeBefore = p->size;
    p->setSelected(true);
    auto resizeHandle = p->handles()[4];
    QGraphicsSceneMouseEvent bp(QEvent::GraphicsSceneMousePress);
    bp.setPos(resizeHandle);
    bp.setScenePos(p->mapToScene(resizeHandle));
    p->mousePressEvent(&bp);
    QGraphicsSceneMouseEvent bm(QEvent::GraphicsSceneMouseMove);
    bm.setScenePos(p->mapToScene(resizeHandle + QPointF(180, 120)));
    p->mouseMoveEvent(&bm);
    qreal sx = p->size.width() / panelSizeBefore.width();
    qreal sy = p->size.height() / panelSizeBefore.height();
    auto ownerLocalAfter =
        p->mapFromScene(breakoutBubble->mapToScene(QPointF()));
    check("panel resize scales breakout bubble position and size",
          QLineF(ownerLocalAfter,
                 {ownerLocalBefore.x() * sx, ownerLocalBefore.y() * sy})
                      .length() < .5 &&
              qAbs(breakoutBubble->size.width() -
                   bubbleSizeBefore.width() * sx) < .5 &&
              qAbs(breakoutBubble->size.height() -
                   bubbleSizeBefore.height() * sy) < .5 &&
              breakoutBubble->fontSize > bubbleFontBefore);
    QGraphicsSceneMouseEvent br(QEvent::GraphicsSceneMouseRelease);
    br.setPos(p->handles()[4]);
    br.setScenePos(p->mapToScene(p->handles()[4]));
    p->mouseReleaseEvent(&br);

    auto *independentImage = new Node("image", p);
    independentImage->image = tiny;
    independentImage->size = {180, 140};
    independentImage->setPos(260, 220);
    w.bind(independentImage);
    auto bubbleSceneBefore = breakoutBubble->mapToScene(QPointF());
    auto breakoutSizeBefore = breakoutBubble->size;
    auto breakoutFontBefore = breakoutBubble->fontSize;
    independentImage->setSelected(true);
    auto ih = independentImage->handles()[4];
    QGraphicsSceneMouseEvent ip(QEvent::GraphicsSceneMousePress);
    ip.setPos(ih);
    ip.setScenePos(independentImage->mapToScene(ih));
    independentImage->mousePressEvent(&ip);
    QGraphicsSceneMouseEvent imove(QEvent::GraphicsSceneMouseMove);
    imove.setScenePos(independentImage->mapToScene(ih + QPointF(90, 70)));
    independentImage->mouseMoveEvent(&imove);
    QGraphicsSceneMouseEvent ir(QEvent::GraphicsSceneMouseRelease);
    ir.setPos(independentImage->handles()[4]);
    ir.setScenePos(independentImage->mapToScene(independentImage->handles()[4]));
    independentImage->mouseReleaseEvent(&ir);
    check("image-only resize never moves or scales bubble",
          QLineF(breakoutBubble->mapToScene(QPointF()), bubbleSceneBefore)
                      .length() < .01 &&
              breakoutBubble->size == breakoutSizeBefore &&
              qFuzzyCompare(breakoutBubble->fontSize, breakoutFontBefore));
  }

'''
if needle not in s:
    raise SystemExit('tests/regression.h: breakout insertion target not found')
s = s.replace(needle, addition, 1)
reg.write_text(s, encoding='utf-8', newline='\n')

print('RC7.7 source transforms applied')
