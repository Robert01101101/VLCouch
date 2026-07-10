import { useEffect, useRef, useState } from 'react'
import PosterCard from './PosterCard'

const DRAG_THRESHOLD = 5
const FRICTION = 0.93
const MIN_VELOCITY = 0.5

function pointerX(ev) {
  return ev.pageX ?? ev.clientX ?? 0
}

export default function Row({ title, subtitle, items, getLink, onPlay, rowId }) {
  const scrollRef = useRef(null)
  const dragRef = useRef({
    active: false,
    startX: 0,
    scrollLeft: 0,
    dragged: false,
    lastX: 0,
    velocity: 0,
  })
  const suppressClickRef = useRef(false)
  const momentumIdRef = useRef(null)
  const [grabbing, setGrabbing] = useState(false)

  useEffect(() => {
    return () => {
      if (momentumIdRef.current != null) {
        cancelAnimationFrame(momentumIdRef.current)
      }
    }
  }, [])

  if (!items || items.length === 0) return null

  const slug = rowId || title.toLowerCase().replace(/\s+/g, '-')

  function cancelMomentum() {
    if (momentumIdRef.current != null) {
      cancelAnimationFrame(momentumIdRef.current)
      momentumIdRef.current = null
    }
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

  function handleClickCapture(e) {
    if (suppressClickRef.current) {
      e.preventDefault()
      e.stopPropagation()
    }
  }

  function handleMouseDown(e) {
    suppressClickRef.current = false
    cancelMomentum()
    if (e.button !== 0) return
    const el = scrollRef.current
    if (!el) return

    const startX = pointerX(e)
    dragRef.current = {
      active: true,
      startX,
      scrollLeft: el.scrollLeft,
      dragged: false,
      lastX: startX,
      velocity: 0,
    }
    setGrabbing(true)

    function handleMouseMove(ev) {
      if (!dragRef.current.active) return
      const x = pointerX(ev)
      const dx = x - dragRef.current.startX
      if (Math.abs(dx) > DRAG_THRESHOLD) {
        dragRef.current.dragged = true
      }
      dragRef.current.velocity = x - dragRef.current.lastX
      dragRef.current.lastX = x
      el.scrollLeft = dragRef.current.scrollLeft - dx
    }

    function handleMouseUp() {
      if (dragRef.current.dragged) {
        suppressClickRef.current = true
        applyMomentum(el, dragRef.current.velocity)
      }
      dragRef.current.active = false
      setGrabbing(false)
      document.removeEventListener('mousemove', handleMouseMove)
      document.removeEventListener('mouseup', handleMouseUp)
    }

    document.addEventListener('mousemove', handleMouseMove)
    document.addEventListener('mouseup', handleMouseUp)
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
        onMouseDown={handleMouseDown}
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
