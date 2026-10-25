import React, { useState, useEffect } from 'react'
import { listStories, createStory } from '../api/client'
import type { CommunityStory, CommunityStoryCreate } from '../types'
import { useAuth } from '../context/AuthContext'

export default function CommunityStories() {
  const { user } = useAuth()
  const [stories, setStories] = useState<CommunityStory[]>([])
  const [loading, setLoading] = useState(true)
  const [submitting, setSubmitting] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [successMessage, setSuccessMessage] = useState<string | null>(null)

  // Form State
  const [showForm, setShowForm] = useState(false)
  const [title, setTitle] = useState('')
  const [storyText, setStoryText] = useState('')
  const [authorName, setAuthorName] = useState(user?.name || '')
  const [condition, setCondition] = useState('')
  const [email, setEmail] = useState('')
  const [instagram, setInstagram] = useState('')
  const [consentAcknowledged, setConsentAcknowledged] = useState(false)

  // Filter State
  const [selectedTopic, setSelectedTopic] = useState<string>('all')
  const [searchQuery, setSearchQuery] = useState('')

  const fetchStories = async () => {
    setLoading(true)
    setError(null)
    try {
      const res = await listStories(50, 0)
      setStories(res.stories)
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : 'Failed to load community stories.')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    fetchStories()
  }, [])

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!storyText.trim() || storyText.trim().length < 10) {
      setError('Please provide a story of at least 10 characters.')
      return
    }
    if (!consentAcknowledged) {
      setError('Please confirm that you understand this story and any contact details will be publicly visible.')
      return
    }

    setSubmitting(true)
    setError(null)

    const payload: CommunityStoryCreate = {
      title: title.trim() || undefined,
      story_text: storyText.trim(),
      author_name: authorName.trim() || 'Community Member',
      condition_or_topic: condition.trim() || undefined,
      contact_email: email.trim() || undefined,
      contact_instagram: instagram.trim().replace(/^@/, '') || undefined,
      consent_acknowledged: true,
    }

    try {
      const newStory = await createStory(payload)
      setStories((prev) => [newStory, ...prev])
      setSuccessMessage('Thank you for sharing your story. It is now published to the community feed.')

      // Reset form
      setTitle('')
      setStoryText('')
      setCondition('')
      setEmail('')
      setInstagram('')
      setConsentAcknowledged(false)
      setShowForm(false)

      setTimeout(() => setSuccessMessage(null), 5000)
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : 'Failed to submit story. Please try again.')
    } finally {
      setSubmitting(false)
    }
  }

  // Derive available topics for filter pills
  const topics = Array.from(
    new Set(
      stories
        .map((s) => s.condition_or_topic)
        .filter((t): t is string => Boolean(t && t.trim()))
    )
  )

  const filteredStories = stories.filter((s) => {
    if (selectedTopic !== 'all') {
      if (s.condition_or_topic?.toLowerCase() !== selectedTopic.toLowerCase()) {
        return false
      }
    }
    if (searchQuery.trim()) {
      const q = searchQuery.trim().toLowerCase()
      const inText = s.story_text.toLowerCase().includes(q)
      const inTitle = (s.title || '').toLowerCase().includes(q)
      const inAuthor = s.author_name.toLowerCase().includes(q)
      const inTopic = (s.condition_or_topic || '').toLowerCase().includes(q)
      if (!inText && !inTitle && !inAuthor && !inTopic) {
        return false
      }
    }
    return true
  })

  return (
    <div className="space-y-8 max-w-4xl mx-auto font-sans">
      {/* Permanent High-Priority Medical Disclaimer */}
      <div className="bg-amber-50/90 border border-amber-300 rounded-2xl p-4 sm:p-5 shadow-subtle text-amber-950 flex items-start gap-3.5">
        <span className="text-xl sm:text-2xl flex-shrink-0 mt-0.5">⚠️</span>
        <div className="text-xs sm:text-sm leading-relaxed">
          <strong className="block font-bold text-amber-950 text-xs sm:text-sm uppercase tracking-wide mb-1">
            Important Notice &bull; Not Medical Advice
          </strong>
          These are personal experiences and coping stories voluntarily shared by individuals.
          They are not medical advice, diagnosis, or treatment recommendations. Every body and medical history is different. Always consult qualified healthcare professionals before making any health decisions.
        </div>
      </div>

      {/* Page Header */}
      <div className="text-center max-w-2xl mx-auto">
        <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-clinical-50 border border-clinical-200 text-clinical-800 text-xs font-bold mb-3 shadow-subtle">
          <span>🌱 Personal Perspectives &amp; Coping</span>
        </div>
        <h1 className="text-3xl sm:text-4xl font-black text-slate-900 tracking-tight">
          Community Recovery Stories
        </h1>
        <p className="mt-2 text-xs sm:text-sm text-slate-600 leading-relaxed">
          A supportive, peer-shared space where individuals talk about what they experienced, what gave them hope or helped them cope, and how they navigated illness.
        </p>

        {/* Share Button CTA */}
        <div className="mt-5">
          <button
            type="button"
            onClick={() => {
              setShowForm(!showForm)
              setError(null)
            }}
            className="px-6 py-2.5 rounded-xl bg-slate-900 hover:bg-slate-800 text-white text-xs font-bold shadow-md transition-all inline-flex items-center gap-2"
          >
            <span>✍️</span>
            <span>{showForm ? 'Close Story Form' : 'Share Your Experience'}</span>
          </button>
        </div>
      </div>

      {/* Success Alert */}
      {successMessage && (
        <div className="p-4 rounded-xl bg-emerald-50 border border-emerald-300 text-emerald-900 text-xs sm:text-sm flex items-center justify-between shadow-subtle animate-in fade-in">
          <div className="flex items-center gap-2">
            <span>✓</span>
            <span className="font-semibold">{successMessage}</span>
          </div>
          <button
            type="button"
            onClick={() => setSuccessMessage(null)}
            className="text-emerald-700 hover:text-emerald-900 font-bold"
          >
            ×
          </button>
        </div>
      )}

      {/* Story Submission Form Card */}
      {showForm && (
        <form
          onSubmit={handleSubmit}
          className="bg-white rounded-2xl border border-slate-200 p-6 sm:p-7 shadow-card space-y-4 animate-in fade-in duration-200"
        >
          <div className="flex items-center justify-between pb-3 border-b border-slate-100">
            <div>
              <h2 className="text-base font-bold text-slate-900">
                Share What Helped You Keep Going
              </h2>
              <p className="text-xs text-slate-500 mt-0.5">
                Your story can provide reassurance to someone facing a similar challenge.
              </p>
            </div>
            <button
              type="button"
              onClick={() => setShowForm(false)}
              className="text-slate-400 hover:text-slate-600 p-1 rounded-lg"
            >
              ✕
            </button>
          </div>

          {error && (
            <div className="p-3 rounded-lg bg-rose-50 border border-rose-200 text-rose-800 text-xs">
              <strong>Please Note:</strong> {error}
            </div>
          )}

          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            <div>
              <label className="block text-xs font-bold text-slate-700 mb-1">
                Your Name or Alias (Optional)
              </label>
              <input
                type="text"
                value={authorName}
                onChange={(e) => setAuthorName(e.target.value)}
                placeholder="e.g. David M., or Anonymous"
                className="w-full px-3.5 py-2 text-xs rounded-xl border border-slate-300 focus:outline-none focus:ring-2 focus:ring-sky-500 text-slate-800"
              />
            </div>

            <div>
              <label className="block text-xs font-bold text-slate-700 mb-1">
                Condition or Topic Tag (Optional)
              </label>
              <input
                type="text"
                value={condition}
                onChange={(e) => setCondition(e.target.value)}
                placeholder="e.g. Type 2 Diabetes, Migraine, Surgery Recovery"
                className="w-full px-3.5 py-2 text-xs rounded-xl border border-slate-300 focus:outline-none focus:ring-2 focus:ring-sky-500 text-slate-800"
              />
            </div>
          </div>

          <div>
            <label className="block text-xs font-bold text-slate-700 mb-1">
              Title or Summary (Optional)
            </label>
            <input
              type="text"
              value={title}
              onChange={(e) => setTitle(e.target.value)}
              placeholder="e.g. Finding my stride after a tough diagnosis"
              className="w-full px-3.5 py-2 text-xs rounded-xl border border-slate-300 focus:outline-none focus:ring-2 focus:ring-sky-500 text-slate-800"
            />
          </div>

          <div>
            <div className="flex items-center justify-between mb-1">
              <label className="block text-xs font-bold text-slate-700">
                Your Story &bull; What You Went Through &amp; What Helped <span className="text-rose-500">*</span>
              </label>
              <span className="text-[11px] text-slate-400">
                {storyText.length} / 5,000 characters
              </span>
            </div>
            <textarea
              rows={6}
              value={storyText}
              onChange={(e) => setStoryText(e.target.value)}
              placeholder="Describe your lived experience: what symptoms or challenges you encountered, the lifestyle adjustments or support systems that helped, and words of encouragement for others..."
              className="w-full px-3.5 py-2.5 text-xs sm:text-sm rounded-xl border border-slate-300 focus:outline-none focus:ring-2 focus:ring-sky-500 text-slate-800 leading-relaxed placeholder:text-slate-400"
              required
              maxLength={5000}
            />
          </div>

          {/* Voluntary Contact Details */}
          <div className="p-4 rounded-xl bg-slate-50 border border-slate-200 space-y-3">
            <div>
              <span className="text-xs font-bold text-slate-800 block">
                Voluntary Public Contact (Optional)
              </span>
              <p className="text-[11px] text-slate-500 mt-0.5">
                Only provide contact details if you would like others dealing with similar situations to reach out. This will be visible on the public story card.
              </p>
            </div>

            <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
              <div>
                <label className="block text-[11px] font-semibold text-slate-600 mb-1">
                  Public Email (Optional)
                </label>
                <input
                  type="email"
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  placeholder="e.g. your.email@example.com"
                  className="w-full px-3 py-1.5 text-xs rounded-lg border border-slate-300 focus:outline-none focus:ring-2 focus:ring-sky-500 text-slate-800"
                />
              </div>

              <div>
                <label className="block text-[11px] font-semibold text-slate-600 mb-1">
                  Public Instagram Handle (Optional)
                </label>
                <input
                  type="text"
                  value={instagram}
                  onChange={(e) => setInstagram(e.target.value)}
                  placeholder="e.g. @your_handle"
                  className="w-full px-3 py-1.5 text-xs rounded-lg border border-slate-300 focus:outline-none focus:ring-2 focus:ring-sky-500 text-slate-800"
                />
              </div>
            </div>
          </div>

          {/* Consent Checkbox */}
          <div className="pt-2">
            <label className="flex items-start gap-2.5 text-xs text-slate-700 cursor-pointer select-none">
              <input
                type="checkbox"
                checked={consentAcknowledged}
                onChange={(e) => setConsentAcknowledged(e.target.checked)}
                className="mt-0.5 w-4 h-4 rounded text-sky-600 focus:ring-sky-500 border-slate-300"
                required
              />
              <span className="leading-relaxed">
                I understand that this story and any contact information I shared will be publicly visible to others. I confirm this is a personal story and not prescriptive medical advice.
              </span>
            </label>
          </div>

          {/* Form Actions */}
          <div className="flex items-center justify-end gap-3 pt-3 border-t border-slate-100">
            <button
              type="button"
              onClick={() => setShowForm(false)}
              className="px-4 py-2 rounded-xl text-xs font-semibold text-slate-600 hover:text-slate-900"
            >
              Cancel
            </button>
            <button
              type="submit"
              disabled={submitting || !storyText.trim() || !consentAcknowledged}
              className="px-6 py-2.5 rounded-xl bg-sky-600 hover:bg-sky-700 text-white text-xs font-bold shadow-sm transition-colors disabled:opacity-50"
            >
              {submitting ? 'Publishing...' : 'Publish Story to Community'}
            </button>
          </div>
        </form>
      )}

      {/* Search & Topic Filters */}
      <div className="space-y-3 bg-white p-4 rounded-2xl border border-slate-200 shadow-subtle">
        <div className="relative">
          <input
            type="text"
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            placeholder="Search stories by topic, symptom, or keyword..."
            className="w-full pl-9 pr-8 py-2 text-xs sm:text-sm rounded-xl border border-slate-300 focus:outline-none focus:ring-2 focus:ring-sky-500 bg-slate-50/50 text-slate-800 placeholder:text-slate-400"
          />
          <span className="absolute left-3 top-2 text-slate-400 text-xs">🔍</span>
          {searchQuery && (
            <button
              type="button"
              onClick={() => setSearchQuery('')}
              className="absolute right-3 top-2 text-slate-400 hover:text-slate-600 text-xs font-bold"
              title="Clear search"
            >
              ✕
            </button>
          )}
        </div>

        {topics.length > 0 && (
          <div className="flex items-center gap-1.5 overflow-x-auto pb-1 text-xs">
            <span className="font-bold text-slate-500 flex-shrink-0 text-[11px] uppercase tracking-wider">
              Topic:
            </span>
            <button
              type="button"
              onClick={() => setSelectedTopic('all')}
              className={`px-3 py-1 rounded-full text-xs font-semibold transition-colors flex-shrink-0 ${
                selectedTopic === 'all'
                  ? 'bg-slate-900 text-white'
                  : 'bg-slate-100 text-slate-600 hover:bg-slate-200 border border-slate-200'
              }`}
            >
              All Stories ({stories.length})
            </button>
            {topics.map((t) => (
              <button
                key={t}
                type="button"
                onClick={() => setSelectedTopic(t)}
                className={`px-3 py-1 rounded-full text-xs font-semibold transition-colors flex-shrink-0 ${
                  selectedTopic.toLowerCase() === t.toLowerCase()
                    ? 'bg-sky-600 text-white'
                    : 'bg-slate-100 text-slate-600 hover:bg-slate-200 border border-slate-200'
                }`}
              >
                {t}
              </button>
            ))}
          </div>
        )}
      </div>

      {/* Stories Feed */}
      {loading ? (
        <div className="space-y-4">
          {[1, 2, 3].map((i) => (
            <div key={i} className="bg-white rounded-2xl border border-slate-200 p-6 animate-pulse space-y-3">
              <div className="h-4 bg-slate-200 rounded w-1/4" />
              <div className="h-5 bg-slate-200 rounded w-1/2" />
              <div className="h-16 bg-slate-100 rounded w-full" />
            </div>
          ))}
        </div>
      ) : filteredStories.length === 0 ? (
        <div className="bg-white rounded-2xl border border-slate-200 p-12 text-center shadow-card">
          <div className="text-4xl mb-3">💬</div>
          <h3 className="text-base font-bold text-slate-800">No Stories in this Category Yet</h3>
          <p className="text-xs text-slate-500 mt-1 max-w-sm mx-auto">
            Be the first to share your lived experience and what helped you cope.
          </p>
          <button
            type="button"
            onClick={() => setShowForm(true)}
            className="mt-4 px-4 py-2 bg-sky-600 text-white rounded-xl text-xs font-bold"
          >
            Share a Story
          </button>
        </div>
      ) : (
        <div className="space-y-5">
          {filteredStories.map((story) => (
            <article
              key={story.story_id}
              className="bg-white rounded-2xl border border-slate-200 p-6 sm:p-7 shadow-subtle hover:shadow-card transition-shadow"
            >
              {/* Header Info */}
              <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2 mb-3">
                <div className="flex items-center gap-2 flex-wrap">
                  <span className="font-bold text-slate-900 text-xs sm:text-sm">
                    {story.author_name}
                  </span>
                  {story.condition_or_topic && (
                    <span className="px-2.5 py-0.5 rounded-full text-[11px] font-semibold bg-clinical-50 text-clinical-800 border border-clinical-200">
                      {story.condition_or_topic}
                    </span>
                  )}
                </div>

                <time className="text-[11px] text-slate-400 font-medium">
                  {new Date(story.created_at).toLocaleDateString(undefined, {
                    year: 'numeric',
                    month: 'short',
                    day: 'numeric',
                  })}
                </time>
              </div>

              {/* Title */}
              {story.title && (
                <h3 className="text-base font-bold text-slate-900 mb-2.5 tracking-tight">
                  {story.title}
                </h3>
              )}

              {/* Story Body */}
              <div className="text-xs sm:text-sm text-slate-700 leading-relaxed whitespace-pre-wrap font-sans bg-slate-50/50 p-4 rounded-xl border border-slate-100">
                {story.story_text}
              </div>

              {/* Optional Contact Footer */}
              {(story.contact_email || story.contact_instagram) && (
                <div className="mt-4 pt-3 border-t border-slate-100 flex items-center justify-between flex-wrap gap-2 text-xs">
                  <span className="text-[11px] text-slate-400 font-medium">
                    Voluntary Contact Shared by Author:
                  </span>
                  <div className="flex items-center gap-2 flex-wrap">
                    {story.contact_email && (
                      <a
                        href={`mailto:${story.contact_email}`}
                        className="inline-flex items-center gap-1.5 px-3 py-1 rounded-lg bg-sky-50 text-sky-700 hover:bg-sky-100 font-semibold text-xs transition-colors border border-sky-100"
                        title="Send email to author"
                      >
                        <span>✉️</span>
                        <span>{story.contact_email}</span>
                      </a>
                    )}
                    {story.contact_instagram && (
                      <a
                        href={`https://instagram.com/${story.contact_instagram}`}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="inline-flex items-center gap-1.5 px-3 py-1 rounded-lg bg-pink-50 text-pink-700 hover:bg-pink-100 font-semibold text-xs transition-colors border border-pink-100"
                        title="View Instagram profile"
                      >
                        <span>📷</span>
                        <span>@{story.contact_instagram}</span>
                      </a>
                    )}
                  </div>
                </div>
              )}
            </article>
          ))}
        </div>
      )}
    </div>
  )
}
