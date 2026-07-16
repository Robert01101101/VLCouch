import { useEffect, useRef, useState } from 'react'
import PosterCard from './PosterCard'

const DRAG_THRESHOLD = 5
const FRICTION = 0.93
const MIN_VELOCITY = 0.5

function pointerX(ev) {
  return ev.pageX ?? ev.clientX ?? 0
}

function matchesPointer(ev, pointerId) {
  if (ev.pointerId == null) return true
  return ev.pointerId === pointerId
}

export default function Row({ title, subtitle, items, getLink, onPlay, rowId }) {
  const scrollRef = useRef(null)
  const dragRef = useRef({
    active: false,
    dragging: false,
    startX: 0,
    scrollLeft: 0,
    dragged: false,
    lastX: 0,
    velocity: 0,
    pointerId: null,
  })
  const suppressClickRef = useRef(false)
  const momentumIdRef = useRef(null)
  const listenersRef = useRef(null)
  const [grabbing, setGrabbing] = useState(false)

  function cancelMomentum() {
    if (momentumIdRef.current != null) {
      cancelAnimationFrame(momentumIdRef.current)
      momentumIdRef.current = null
    }
  }

  function removeDragListeners() {
    const listeners = listenersRef.current
    if (!listeners) return
    const { el, onMove, onUp, onCancel, onBlur } = listeners
    window.removeEventListener('pointermove', onMove)
    window.removeEventListener('pointerup', onUp)
    window.removeEventListener('pointercancel', onCancel)
    window.removeEventListener('blur', onBlur)
    if (listeners.pointerId != null) {
      try {
        el.releasePointerCapture(listeners.pointerId)
      } catch {
        // Pointer may already be released.
      }
    }
    listenersRef.current = null
  }

  function endDrag() {
    if (!dragRef.current.active) return
    const el = scrollRef.current
    if (dragRef.current.dragged && el) {
      suppressClickRef.current = true
      applyMomentum(el, dragRef.current.velocity)
    }
    dragRef.current.active = false
    dragRef.current.dragging = false
    dragRef.current.pointerId = null
    setGrabbing(false)
    removeDragListeners()
  }

  function applyMomentum(el, initialVelocity) {
    cancelMomentum()
    let velocity = initialVelocity
    if (Math.abs(velocity) < MIN_VELOCITY) return

    function tick() {
      if (Math.abs(velocity) < MIN_VELOCITY) {
        momentumIdRef.current = null
        return
      }
      el.scrollLeft -= velocity
      velocity *= FRICTION
      momentumIdRef.current = requestAnimationFrame(tick)
    }
    momentumIdRef.current = requestAnimationFrame(tick)
  }

  useEffect(() => {
    return () => {
      cancelMomentum()
      endDrag()
    }
  }, [])

  if (!items || items.length === 0) return null

  const slug = rowId || title.toLowerCase().replace(/\s+/g, '-')

  function handleClickCapture(e) {
    if (suppressClickRef.current) {
      suppressClickRef.current = false
      e.preventDefault()
      e.stopPropagation()
    }
  }

  function handleDragStart(e) {
    e.preventDefault()
  }

  function handlePointerDown(e) {
    suppressClickRef.current = false
    cancelMomentum()
    if (e.button !== 0) return
    const el = scrollRef.current
    if (!el) return

    endDrag()

    const startX = pointerX(e)
    dragRef.current = {
      active: true,
      dragging: false,
      startX,
      scrollLeft: el.scrollLeft,
      dragged: false,
      lastX: startX,
      velocity: 0,
      pointerId: e.pointerId,
    }

    function handlePointerMove(ev) {
      if (!dragRef.current.active || !matchesPointer(ev, dragRef.current.pointerId)) return
      const x = pointerX(ev)
      const dx = x - dragRef.current.startX

      if (!dragRef.current.dragging) {
        if (Math.abs(dx) <= DRAG_THRESHOLD) return
        dragRef.current.dragging = true
        dragRef.current.dragged = true
        setGrabbing(true)
        try {
          el.setPointerCapture(ev.pointerId)
        } catch {
          // jsdom and some browsers may not support capture.
        }
        ev.preventDefault()
      }

      dragRef.current.velocity = x - dragRef.current.lastX
      dragRef.current.lastX = x
      el.scrollLeft = dragRef.current.scrollLeft - dx
    }

    function handlePointerUp(ev) {
      if (!matchesPointer(ev, dragRef.current.pointerId)) return
      endDrag()
    }

    function handlePointerCancel(ev) {
      if (!matchesPointer(ev, dragRef.current.pointerId)) return
      endDrag()
    }

    function handleBlur() {
      endDrag()
    }

    window.addEventListener('pointermove', handlePointerMove)
    window.addEventListener('pointerup', handlePointerUp)
    window.addEventListener('pointercancel', handlePointerCancel)
    window.addEventListener('blur', handleBlur)
    listenersRef.current = {
      el,
      onMove: handlePointerMove,
      onUp: handlePointerUp,
      onCancel: handlePointerCancel,
      onBlur: handleBlur,
      pointerId: e.pointerId,
    }
  }

  function handlePlay(item) {
    if (suppressClickRef.current) {
      suppressClickRef.current = false
      return
    }
    onPlay?.(item)
  }

  return (
    <section className="mb-10" data-testid={`browse-row-${slug}`}>
      <div className="flex items-baseline gap-3 mb-4 px-6">
        <h2 className="text-2xl font-semibold">{title}</h2>
        {subtitle && <span className="text-sm text-gray-500">{subtitle}</span>}
      </div>
      <div
        ref={scrollRef}
        data-testid={`browse-row-scroll-${slug}`}
        className={`flex gap-4 overflow-x-auto pb-4 pl-6 scrollbar-hide select-none ${
          grabbing ? 'cursor-grabbing' : 'cursor-grab'
        }`}
        onPointerDown={handlePointerDown}
        onDragStart={handleDragStart}
        onClickCapture={handleClickCapture}
      >
        {items.map((item) => {
          const link = getLink ? getLink(item) : undefined
          const play =
            onPlay && (!item.item_type || item.item_type === 'movie')
              ? handlePlay
              : undefined
          return (
            <PosterCard
              key={`${item.item_type || 'item'}-${item.id}`}
              item={item}
              to={link}
              onPlay={play}
            />
          )
        })}
      </div>
    </section>
  )
}
