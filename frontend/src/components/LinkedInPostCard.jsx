import { useState } from 'react'
import { ThumbsUp, MessageSquare, ExternalLink, User, Clock, Tag } from 'lucide-react'

const ROLE_COLORS = {
  'AI Engineer':               'bg-blue-100 text-blue-700 border-blue-200',
  'ML Engineer':               'bg-purple-100 text-purple-700 border-purple-200',
  'Machine Learning Engineer': 'bg-purple-100 text-purple-700 border-purple-200',
  'LLM Engineer':              'bg-cyan-100 text-cyan-700 border-cyan-200',
  'GenAI Engineer':            'bg-pink-100 text-pink-700 border-pink-200',
  'Data Scientist':            'bg-emerald-100 text-emerald-700 border-emerald-200',
  'Python Developer':          'bg-indigo-100 text-indigo-700 border-indigo-200',
  'MLOps Engineer':            'bg-amber-100 text-amber-700 border-amber-200',
  'NLP Engineer':              'bg-lime-100 text-lime-700 border-lime-200',
  'Deep Learning Engineer':    'bg-red-100 text-red-700 border-red-200',
  'RAG Developer':             'bg-fuchsia-100 text-fuchsia-700 border-fuchsia-200',
  'Agentic AI':                'bg-violet-100 text-violet-700 border-violet-200',
  // .NET domain
  '.NET Developer':            'bg-red-100 text-red-700 border-red-200',
  'C# Developer':              'bg-red-100 text-red-700 border-red-200',
  'React Developer':           'bg-cyan-100 text-cyan-700 border-cyan-200',
  'Angular Developer':         'bg-red-100 text-red-600 border-red-200',
  // SAP domain
  'SAP TM':                    'bg-blue-100 text-blue-700 border-blue-200',
  'SAP Transport Management':  'bg-blue-100 text-blue-700 border-blue-200',
  'SAP TM Architect':          'bg-blue-100 text-blue-700 border-blue-200',
  'SAP SCM Consultant':        'bg-sky-100 text-sky-700 border-sky-200',
}

function avatarInitial(name) {
  if (!name) return 'L'
  const parts = name.trim().split(' ')
  return parts.length >= 2
    ? (parts[0][0] + parts[1][0]).toUpperCase()
    : parts[0][0].toUpperCase()
}

function fmtCount(n) {
  if (!n || n === 0) return '0'
  if (n >= 1000) return `${(n / 1000).toFixed(1)}k`
  return n.toLocaleString()
}

export default function LinkedInPostCard({ post }) {
  const [expanded, setExpanded] = useState(false)

  const content    = post.content || ''
  const isLong     = content.length > 300
  const displayed  = !expanded && isLong ? content.slice(0, 300) + '…' : content
  const roleColor  = ROLE_COLORS[post.role_keyword] ?? 'bg-gray-100 text-gray-600 border-gray-200'
  const initials   = avatarInitial(post.author_name)

  const highlightText = (text) => {
    const parts = text.split(/(#\w+|@\w+)/g)
    return parts.map((part, i) =>
      part.startsWith('#') || part.startsWith('@')
        ? <span key={i} className="text-red-500 font-medium">{part}</span>
        : part
    )
  }

  return (
    <article className="card p-4 flex flex-col gap-3">
      {/* Role tag */}
      <div className="flex items-center justify-between gap-2">
        <span className={`badge border text-[10px] leading-tight ${roleColor}`}>
          <Tag size={9} className="mr-1 inline" />
          {post.role_keyword || 'LinkedIn'}
        </span>
        <span className="badge bg-blue-50 text-blue-600 text-[10px] border border-blue-100">
          LinkedIn Post
        </span>
      </div>

      {/* Author */}
      <div className="flex items-start gap-2.5">
        {post.author_url ? (
          <a href={post.author_url} target="_blank" rel="noopener noreferrer" className="shrink-0">
            <div className="w-9 h-9 rounded-full bg-red-100 border border-red-200 flex items-center justify-center text-red-600 text-xs font-bold hover:bg-red-200 transition-colors">
              {initials}
            </div>
          </a>
        ) : (
          <div className="w-9 h-9 rounded-full bg-gray-100 border border-gray-200 flex items-center justify-center text-gray-400 shrink-0">
            <User size={14} />
          </div>
        )}
        <div className="min-w-0">
          {post.author_name ? (
            post.author_url ? (
              <a href={post.author_url} target="_blank" rel="noopener noreferrer"
                className="text-sm font-semibold text-gray-900 hover:text-red-600 transition-colors truncate block">
                {post.author_name}
              </a>
            ) : (
              <p className="text-sm font-semibold text-gray-900 truncate">{post.author_name}</p>
            )
          ) : (
            <p className="text-sm font-semibold text-gray-400 italic">Unknown author</p>
          )}
          {post.author_title && (
            <p className="text-[11px] text-gray-400 line-clamp-1">{post.author_title}</p>
          )}
        </div>
      </div>

      {/* Post content */}
      {content ? (
        <div className="text-sm text-gray-700 whitespace-pre-wrap leading-relaxed">
          {highlightText(displayed)}
          {isLong && (
            <button
              onClick={() => setExpanded(e => !e)}
              className="ml-1 text-red-500 hover:text-red-600 text-xs font-medium transition-colors"
            >
              {expanded ? 'show less' : 'see more'}
            </button>
          )}
        </div>
      ) : (
        <p className="text-sm text-gray-400 italic">No content preview available.</p>
      )}

      {/* Footer */}
      <div className="flex items-center justify-between pt-2 border-t border-gray-100 gap-2 flex-wrap">
        <div className="flex items-center gap-3 text-xs text-gray-400">
          {post.posted_at && (
            <span className="flex items-center gap-1">
              <Clock size={10} />
              {post.posted_at}
            </span>
          )}
          <span className="flex items-center gap-1">
            <ThumbsUp size={10} />
            {fmtCount(post.likes_count)}
          </span>
          <span className="flex items-center gap-1">
            <MessageSquare size={10} />
            {fmtCount(post.comments_count)}
          </span>
        </div>

        <a
          href={post.post_url}
          target="_blank"
          rel="noopener noreferrer"
          className="flex items-center gap-1 px-2.5 py-1 rounded-md text-[11px] font-semibold
            bg-red-600 text-white hover:bg-red-500 transition-all shrink-0"
        >
          <ExternalLink size={10} />
          View Post
        </a>
      </div>
    </article>
  )
}
