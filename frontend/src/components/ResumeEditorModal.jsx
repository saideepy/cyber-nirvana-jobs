import { useState, useRef } from 'react'
import { X, Upload, FileText, CheckCircle2, ArrowRight, Download, RotateCcw, AlertCircle } from 'lucide-react'

const ACCEPT = '.pdf,.docx,.doc,.txt'

function MatchBar({ label, value, color }) {
  return (
    <div className="flex items-center gap-3">
      <span className="text-xs text-gray-500 w-24 shrink-0">{label}</span>
      <div className="flex-1 bg-gray-100 rounded-full h-2">
        <div className={`h-2 rounded-full transition-all duration-700 ${color}`} style={{ width: `${Math.min(value, 100)}%` }} />
      </div>
      <span className="text-sm font-bold w-10 text-right text-gray-800">{value}%</span>
    </div>
  )
}

function ChangeBadge({ type }) {
  const cfg = {
    modified: 'bg-blue-100 text-blue-700 border-blue-200',
    added:    'bg-green-100 text-green-700 border-green-200',
    removed:  'bg-red-100 text-red-600 border-red-200',
  }[type] ?? 'bg-gray-100 text-gray-600 border-gray-200'
  const label = { modified: 'swap', added: 'add', removed: 'remove' }[type] ?? type
  return (
    <span className={`inline-flex items-center px-1.5 py-0.5 rounded text-[10px] font-semibold border uppercase tracking-wide ${cfg}`}>
      {label}
    </span>
  )
}

export default function ResumeEditorModal({ onClose, authFetch }) {
  const [step,     setStep]     = useState('input')
  const [file,     setFile]     = useState(null)
  const [jd,       setJd]       = useState('')
  const [result,   setResult]   = useState(null)
  const [errMsg,   setErrMsg]   = useState('')
  const [dragging, setDragging] = useState(false)
  const fileRef = useRef(null)

  const handleFile = (f) => {
    if (!f) return
    const ext = f.name.split('.').pop().toLowerCase()
    if (!['pdf','docx','doc','txt'].includes(ext)) { setErrMsg('Unsupported file type. Use PDF, DOCX, or TXT.'); return }
    if (f.size > 5 * 1024 * 1024) { setErrMsg('File too large (max 5 MB).'); return }
    setFile(f); setErrMsg('')
  }

  const handleDrop = (e) => { e.preventDefault(); setDragging(false); handleFile(e.dataTransfer.files[0]) }

  const handleSubmit = async () => {
    if (!file || !jd.trim() || jd.trim().length < 50) return
    setStep('loading'); setErrMsg('')
    try {
      const form = new FormData()
      form.append('resume_file', file)
      form.append('job_description', jd.trim())
      const res  = await authFetch('/api/resume/optimize', { method: 'POST', body: form })
      const data = await res.json()
      if (!res.ok) throw new Error(data.detail || 'Optimization failed')
      setResult(data)
      setStep('result')
    } catch (e) {
      setErrMsg(e.message || 'Something went wrong. Please try again.')
      setStep('error')
    }
  }

  const handleDownload = () => {
    if (!result?.docx_base64) return
    const binary = atob(result.docx_base64)
    const bytes  = new Uint8Array(binary.length)
    for (let i = 0; i < binary.length; i++) bytes[i] = binary.charCodeAt(i)
    const blob = new Blob([bytes], { type: 'application/vnd.openxmlformats-officedocument.wordprocessingml.document' })
    const url  = URL.createObjectURL(blob)
    const a    = document.createElement('a')
    a.href = url; a.download = `optimized_resume_${Date.now()}.docx`; a.click()
    URL.revokeObjectURL(url)
  }

  const handleReset = () => { setStep('input'); setResult(null); setErrMsg('') }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/30 backdrop-blur-sm">
      <div className="bg-white rounded-2xl shadow-2xl border border-gray-200 w-full max-w-3xl max-h-[90vh] flex flex-col">

        {/* Header */}
        <div className="flex items-center justify-between px-6 py-4 border-b border-gray-100 shrink-0">
          <div className="flex items-center gap-3">
            <div className="w-9 h-9 rounded-xl bg-red-100 flex items-center justify-center">
              <FileText size={18} className="text-red-600" />
            </div>
            <div>
              <h2 className="font-bold text-gray-900 text-base leading-none">Resume Editor</h2>
              <p className="text-[11px] text-gray-400 mt-0.5">AI-powered ATS optimization</p>
            </div>
          </div>
          <button onClick={onClose} className="w-8 h-8 flex items-center justify-center rounded-lg text-gray-400 hover:text-gray-700 hover:bg-gray-100 transition-all">
            <X size={18} />
          </button>
        </div>

        {/* Body */}
        <div className="flex-1 overflow-y-auto px-6 py-5 min-h-0">

          {/* INPUT / ERROR */}
          {(step === 'input' || step === 'error') && (
            <div className="space-y-5">
              <div>
                <label className="sidebar-label">Your Resume</label>
                <div
                  onDragOver={e => { e.preventDefault(); setDragging(true) }}
                  onDragLeave={() => setDragging(false)}
                  onDrop={handleDrop}
                  onClick={() => fileRef.current?.click()}
                  className={`flex flex-col items-center justify-center gap-2 p-6 rounded-xl border-2 border-dashed cursor-pointer transition-all
                    ${dragging ? 'border-red-400 bg-red-50' : file ? 'border-green-300 bg-green-50' : 'border-gray-200 bg-gray-50 hover:border-red-300 hover:bg-red-50/40'}`}
                >
                  <input ref={fileRef} type="file" accept={ACCEPT} className="hidden" onChange={e => handleFile(e.target.files[0])} />
                  {file ? (
                    <>
                      <CheckCircle2 size={24} className="text-green-500" />
                      <span className="text-sm font-semibold text-green-700">{file.name}</span>
                      <span className="text-xs text-gray-400">{(file.size / 1024).toFixed(0)} KB · click to replace</span>
                    </>
                  ) : (
                    <>
                      <Upload size={24} className="text-gray-400" />
                      <span className="text-sm font-semibold text-gray-600">Drop your resume here or click to upload</span>
                      <span className="text-xs text-gray-400">PDF, DOCX, TXT · max 5 MB</span>
                    </>
                  )}
                </div>
              </div>

              <div>
                <label className="sidebar-label">Job Description</label>
                <textarea
                  value={jd} onChange={e => setJd(e.target.value)}
                  placeholder="Paste the full job description here — the more detail the better…"
                  rows={9} className="input w-full resize-none leading-relaxed"
                />
                <p className="text-[11px] text-gray-400 mt-1">{jd.length} characters · min 50 required</p>
              </div>

              {errMsg && (
                <div className="flex items-start gap-2 p-3 bg-red-50 border border-red-200 rounded-lg text-sm text-red-600">
                  <AlertCircle size={15} className="shrink-0 mt-0.5" />{errMsg}
                </div>
              )}
            </div>
          )}

          {/* LOADING */}
          {step === 'loading' && (
            <div className="flex flex-col items-center justify-center py-16 gap-4">
              <div className="relative">
                <div className="w-16 h-16 rounded-full border-4 border-red-100 border-t-red-500 animate-spin" />
                <FileText size={20} className="absolute inset-0 m-auto text-red-400" />
              </div>
              <div className="text-center">
                <p className="font-semibold text-gray-800">Optimizing your resume…</p>
                <p className="text-sm text-gray-400 mt-1">Analyzing and enhancing your resume — this takes 10–30 seconds</p>
              </div>
            </div>
          )}

          {/* RESULT */}
          {step === 'result' && result && (
            <div className="space-y-5">
              {/* Match scores */}
              <div className="bg-gray-50 rounded-xl p-4 space-y-3">
                <h3 className="text-xs font-semibold text-gray-500 uppercase tracking-wider">ATS Match Score</h3>
                <MatchBar label="Before" value={result.match_before ?? 0} color="bg-gray-400" />
                <MatchBar label="After"  value={result.match_after  ?? 0} color="bg-green-500" />
                <div className="flex items-center gap-2 pt-1">
                  <span className="text-xs text-gray-500">Improvement</span>
                  <span className="text-sm font-bold text-green-600">
                    +{Math.max(0, (result.match_after ?? 0) - (result.match_before ?? 0))}%
                  </span>
                  <ArrowRight size={12} className="text-green-500" />
                  <span className="text-sm font-bold text-green-600">{result.match_after ?? 0}% ATS match</span>
                </div>
              </div>

              {/* Changes */}
              {result.changes?.length > 0 && (
                <div>
                  <h3 className="text-xs font-semibold text-gray-500 uppercase tracking-wider mb-2">Changes Made ({result.changes.length})</h3>
                  <div className="space-y-1.5 max-h-48 overflow-y-auto pr-1">
                    {result.changes.map((c, i) => (
                      <div key={i} className="flex items-start gap-2 p-2 bg-white rounded-lg border border-gray-100">
                        <ChangeBadge type={c.type} />
                        <span className="text-xs text-gray-600 leading-snug">{c.description}</span>
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {/* Download */}
              {result.docx_base64 ? (
                <div className="flex items-center justify-center pt-2">
                  <button onClick={handleDownload}
                    className="flex items-center gap-2 px-5 py-2.5 rounded-xl text-sm font-semibold bg-red-600 text-white hover:bg-red-500 transition-all shadow-sm">
                    <Download size={15} />
                    Download Optimized Resume (.docx)
                  </button>
                </div>
              ) : (
                <p className="text-xs text-center text-gray-400">Upload a .docx file to get a downloadable optimized version.</p>
              )}
            </div>
          )}
        </div>

        {/* Footer */}
        <div className="flex items-center justify-between px-6 py-4 border-t border-gray-100 shrink-0">
          {step === 'result' ? (
            <>
              <button onClick={handleReset} className="btn-ghost text-sm gap-1.5"><RotateCcw size={13} /> Optimize another</button>
              <button onClick={onClose} className="btn-primary text-sm">Done</button>
            </>
          ) : step === 'loading' ? (
            <>
              <span className="text-xs text-gray-400">Please wait…</span>
              <button onClick={onClose} className="btn-ghost text-sm">Cancel</button>
            </>
          ) : (
            <>
              <button onClick={onClose} className="btn-ghost text-sm">Cancel</button>
              <button onClick={handleSubmit} disabled={!file || jd.trim().length < 50}
                className="btn-primary text-sm disabled:opacity-40 disabled:cursor-not-allowed">
                <FileText size={14} />
                Optimize Resume
              </button>
            </>
          )}
        </div>

      </div>
    </div>
  )
}
