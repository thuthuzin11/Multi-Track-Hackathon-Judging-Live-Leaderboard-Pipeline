import React, { useState } from 'react'
import { toLocalString, toDatetimeLocalValue } from '../datetime.js'

/**
 * A small generic CRUD panel: a create form on top, a table of existing
 * rows below with inline Edit / Delete. Used identically for Events,
 * Tracks, Teams, and Judges so the admin page doesn't need four
 * hand-written near-duplicate forms.
 *
 * fields: [{ key, label, type: 'text'|'select'|'password'|'datetime-local', options?, numeric?, dynamicMin? }]
 * `options` (for type 'select') is an array of { value, label }.
 * `dynamicMin: true` on a datetime-local field stops the picker from
 * offering any time earlier than "now" (recomputed on every render).
 * extraColumns (optional): [{ label, render(item) }] -- read-only computed
 * columns appended after the editable fields (e.g. a status badge).
 */
export default function EntityManager({ title, items, fields, onCreate, onUpdate, onDelete, idKey = 'id', extraColumns = [] }) {
  const emptyForm = Object.fromEntries(fields.map((f) => [f.key, '']))
  const [form, setForm] = useState(emptyForm)
  const [editingId, setEditingId] = useState(null)
  const [editValues, setEditValues] = useState({})
  const [error, setError] = useState(null)
  const [notice, setNotice] = useState(null)

  const flash = (msg) => {
    setNotice(msg)
    setTimeout(() => setNotice(null), 2500)
  }

  const startEdit = (item) => {
    setEditingId(item[idKey])
    setEditValues(Object.fromEntries(fields.map((f) => [f.key, toInputValue(f, item[f.key])])))
    setError(null)
  }
  const cancelEdit = () => {
    setEditingId(null)
    setEditValues({})
  }

  const handleCreate = async (e) => {
    e.preventDefault()
    setError(null)
    try {
      const payload = buildPayload(fields, form)
      await onCreate(payload)
      setForm(emptyForm)
      flash('Created.')
    } catch (err) {
      setError(err.message)
    }
  }

  const handleSaveEdit = async (id) => {
    setError(null)
    try {
      const payload = buildPayload(fields, editValues)
      // Don't send an empty password on edit -- it means "keep current".
      fields.forEach((f) => {
        if (f.type === 'password' && !payload[f.key]) delete payload[f.key]
      })
      await onUpdate(id, payload)
      cancelEdit()
      flash('Updated.')
    } catch (err) {
      setError(err.message)
    }
  }

  const handleDelete = async (id) => {
    if (!window.confirm('Delete this? This cannot be undone.')) return
    setError(null)
    try {
      await onDelete(id)
      flash('Deleted.')
    } catch (err) {
      setError(err.message)
    }
  }

  const renderInput = (field, value, onChange) => {
    if (field.type === 'select') {
      return (
        <select value={value} onChange={(e) => onChange(e.target.value)}>
          <option value="">-- {field.label} --</option>
          {field.options.map((o) => (
            <option key={o.value} value={o.value}>{o.label}</option>
          ))}
        </select>
      )
    }
    if (field.type === 'datetime-local') {
      return (
        <input
          type="datetime-local"
          value={value}
          min={field.dynamicMin ? toDatetimeLocalValue(new Date().toISOString()) : undefined}
          onChange={(e) => onChange(e.target.value)}
        />
      )
    }
    return (
      <input
        type={field.type === 'password' ? 'password' : 'text'}
        placeholder={field.editPlaceholder || field.label}
        value={value}
        onChange={(e) => onChange(e.target.value)}
      />
    )
  }

  const labelFor = (field, item) => {
    if (field.type === 'select') {
      const opt = field.options.find((o) => String(o.value) === String(item[field.key]))
      return opt ? opt.label : item[field.key]
    }
    if (field.type === 'datetime-local') {
      return item[field.key] ? toLocalString(item[field.key]) : <span className="muted">not set</span>
    }
    return item[field.key]
  }

  const totalCols = fields.length + extraColumns.length + 1

  return (
    <div className="entity-manager">
      <h3>{title}</h3>

      <form onSubmit={handleCreate} className="entity-create-form">
        {fields.map((f) => (
          <React.Fragment key={f.key}>
            {renderInput(f, form[f.key], (v) => setForm((s) => ({ ...s, [f.key]: v })))}
          </React.Fragment>
        ))}
        <button type="submit">Add</button>
      </form>

      {error && <p className="error">{error}</p>}
      {notice && <p className="success">{notice}</p>}

      <div className="table-scroll">
        <table className="results-table entity-table">
          <thead>
            <tr>
              {fields.map((f) => <th key={f.key}>{f.label}</th>)}
              {extraColumns.map((c) => <th key={c.label}>{c.label}</th>)}
              <th></th>
            </tr>
          </thead>
          <tbody>
            {items.map((item) => {
              const isEditing = editingId === item[idKey]
              return (
                <tr key={item[idKey]}>
                  {fields.map((f) => (
                    <td key={f.key}>
                      {isEditing
                        ? renderInput(f, editValues[f.key], (v) => setEditValues((s) => ({ ...s, [f.key]: v })))
                        : (f.type === 'password' ? '••••••••' : labelFor(f, item))}
                    </td>
                  ))}
                  {extraColumns.map((c) => (
                    <td key={c.label}>{c.render(item)}</td>
                  ))}
                  <td className="row-actions">
                    {isEditing ? (
                      <>
                        <button onClick={() => handleSaveEdit(item[idKey])} className="small primary-outline">Save</button>
                        <button onClick={cancelEdit} className="small">Cancel</button>
                      </>
                    ) : (
                      <>
                        <button onClick={() => startEdit(item)} className="small">Edit</button>
                        <button onClick={() => handleDelete(item[idKey])} className="small danger">Delete</button>
                      </>
                    )}
                  </td>
                </tr>
              )
            })}
            {items.length === 0 && (
              <tr><td colSpan={totalCols} className="empty">Nothing here yet.</td></tr>
            )}
          </tbody>
        </table>
      </div>
    </div>
  )
}

// ISO datetime from the server -> value the <input type="datetime-local">
// can display, in the viewer's own local time (minute precision).
function toInputValue(field, value) {
  if (field.type === 'datetime-local' && value) {
    return toDatetimeLocalValue(value)
  }
  return value ?? ''
}

function buildPayload(fields, values) {
  const payload = { ...values }
  fields.forEach((f) => {
    if (f.numeric && payload[f.key] !== '') payload[f.key] = Number(payload[f.key])
    if (f.type === 'datetime-local') {
      // <input type="datetime-local"> gives local time with no timezone;
      // treat it as local and convert to a full ISO string for the API.
      payload[f.key] = payload[f.key] ? new Date(payload[f.key]).toISOString() : null
    }
  })
  return payload
}
