import './ArchetypeSelect.css'

export default function ArchetypeSelect({ current, compatibles, onChange }) {
  const options = [current, ...compatibles.filter((a) => a !== current)]
  const disabled = compatibles.length === 0

  return (
    <div className="archetype-select-wrap">
      <label className="archetype-select-label">切换版式：</label>
      <select
        className="archetype-select"
        value={current}
        onChange={(e) => onChange(e.target.value)}
        disabled={disabled}
      >
        {options.map((arch) => (
          <option key={arch} value={arch}>
            {arch}
            {arch === current ? ' (当前)' : ''}
          </option>
        ))}
      </select>
    </div>
  )
}
