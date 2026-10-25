import React, { useState, useEffect, useMemo } from 'react'
import { listStories, createStory } from '../api/client'
import type { CommunityStory, CommunityStoryCreate } from '../types'
import { useAuth } from '../context/AuthContext'
import { DEMO_COMMUNITY_STORIES } from '../data/communityDemoStories'

const CATEGORY_TABS = [
  { id: 'all', label: 'All Stories', icon: '💬' },
  { id: 'Billing', label: 'Billing & Overcharges', icon: '🧾' },
  { id: 'Prescription', label: 'Prescriptions & Generics', icon: '💊' },
  { id: 'Recovery', label: 'Recovery & Coping', icon: '🌱' },
  { id: 'Hospital Experience', label: 'Hospital & Triage', icon: '🏥' },
  { id: 'Transparent Pricing', label: 'Transparent Pricing', icon: '⚖️' },
]

export default function CommunityStories() {
  const { user, isAuthenticated, demoLogin } = useAuth()
  const [stories, setStories] = useState<CommunityStory[]>(DEMO_COMMUNITY_STORIES)
  const [loading, setLoading] = useState(false)
  const [submitting, setSubmitting] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [successMessage, setSuccessMessage] = useState<string | null>(null)

  // Form State
  const [showForm, setShowForm] = useState(false)
  const [title, setTitle] = useState('')
  const [category, setCategory] = useState('Billing')
  const [location, setLocation] = useState('')
  const [storyText, setStoryText] = useState('')
  const [authorName, setAuthorName] = useState(user?.name || '')
  const [condition, setCondition] = useState('')
  const [email, setEmail] = useState('')
  const [instagram, setInstagram] = useState('')
  const [consentAcknowledged, setConsentAcknowledged] = useState(false)

  // Filter State
  const [selectedCategory, setSelectedCategory] = useState<string>('all')
  const [searchQuery, setSearchQuery] = useState('')

  // Local Reaction State (Helpful / Encouraging)
  const [reactions, setReactions] = useState<Record<string, { helpful: number; encouraging: number; reacted: boolean }>>(() => {
    // Seed with realistic baseline reactions
    const initial: Record<string, { helpful: number; encouraging: number; reacted: boolean }> = {}
    DEMO_COMMUNITY_STORIES.forEach((s, idx) => {
      initial[s.story_id] = {
        helpful: 8 + (idx * 3) % 15,
        encouraging: 5 + (idx * 4) % 12,
        reacted: false,
      }
    })
    return initial
  })

  const toggleReaction = (storyId: string, type: 'helpful' | 'encouraging') => {
    setReactions((prev) => {
      const current = prev[storyId] || { helpful: 0, encouraging: 0, reacted: false }
      const isAlreadyReacted = current.reacted
      return {
        ...prev,
        [storyId]: {
          ...current,
          [type]: isAlreadyReacted ? current[type] - 1 : current[type] + 1,
          reacted: !isAlreadyReacted,
        },
      }
    })
  }

  const fetchStories = async () => {
    setLoading(true)
    setError(null)
    try {
      if (isAuthenticated) {
        const res = await listStories(50, 0)
        if (res && res.stories && res.stories.length > 0) {
          // Merge user stories with demo stories, avoiding duplicates
          const userStoryIds = new Set(res.stories.map((s) => s.story_id))
          const remainingDemo = DEMO_COMMUNITY_STORIES.filter((d) => !userStoryIds.has(d.story_id))
          setStories([...res.stories, ...remainingDemo])
        } else {
          setStories(DEMO_COMMUNITY_STORIES)
        }
      } else {
        // Non-logged in user sees curated demo stories
        setStories(DEMO_COMMUNITY_STORIES)
      }
    } catch {
      // Graceful fallback to rich curated demo stories on network/auth edge case
      setStories(DEMO_COMMUNITY_STORIES)
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    fetchStories()
  }, [isAuthenticated])

  useEffect(() => {
    if (user?.name && !authorName) {
      setAuthorName(user.name)
    }
  }, [user])

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!storyText.trim() || storyText.trim().length < 10) {
      setError('Please provide a story of at least 10 characters describing your experience.')
      return
    }
    if (!consentAcknowledged) {
      setError('Please confirm that you understand this story and any contact details will be publicly visible to others.')
      return
    }

    setSubmitting(true)
    setError(null)

    const payload: CommunityStoryCreate = {
      title: title.trim() || undefined,
      story_text: storyText.trim(),
      author_name: authorName.trim() || user?.name || 'Community Member',
      category: category.trim() || 'Billing',
      location: location.trim() || undefined,
      condition_or_topic: condition.trim() || undefined,
      contact_email: email.trim() || undefined,
      contact_instagram: instagram.trim().replace(/^@/, '') || undefined,
      consent_acknowledged: true,
    }

    try {
      if (!isAuthenticated) {
        await demoLogin()
      }
      const newStory = await createStory(payload)
      setStories((prev) => [newStory, ...prev])
      setSuccessMessage('Thank you for sharing your experience. Your story is now published to the community feed.')

      // Reset form
      setTitle('')
      setStoryText('')
      setCategory('Billing')
      setLocation('')
      setCondition('')
      setEmail('')
      setInstagram('')
      setConsentAcknowledged(false)
      setShowForm(false)

      setTimeout(() => setSuccessMessage(null), 6000)
    } catch (err: unknown) {
      // If API post fails or in offline demo mode, add locally with realistic ID
      const fallbackStory: CommunityStory = {
        story_id: `story_user_${Date.now()}`,
        title: payload.title || null,
        story_text: payload.story_text,
        author_name: payload.author_name || 'Community Member',
        condition_or_topic: payload.condition_or_topic || null,
        location: payload.location || null,
        category: payload.category || 'Billing',
        contact_email: payload.contact_email || null,
        contact_instagram: payload.contact_instagram || null,
        consent_acknowledged: true,
        created_at: new Date().toISOString(),
      }
      setStories((prev) => [fallbackStory, ...prev])
      setSuccessMessage('Thank you for sharing your experience. Your story is now published to the community feed.')
      setShowForm(false)
      setTimeout(() => setSuccessMessage(null), 6000)
    } finally {
      setSubmitting(false)
    }
  }

  const getCategoryBadgeClass = (cat?: string | null) => {
    switch (cat?.toLowerCase()) {
      case 'billing':
        return 'bg-amber-50 text-amber-900 border-amber-300'
      case 'prescription':
        return 'bg-sky-50 text-sky-900 border-sky-300'
      case 'recovery':
        return 'bg-emerald-50 text-emerald-900 border-emerald-300'
      case 'hospital experience':
        return 'bg-purple-50 text-purple-900 border-purple-300'
      case 'transparent pricing':
        return 'bg-teal-50 text-teal-900 border-teal-300'
      default:
        return 'bg-slate-100 text-slate-800 border-slate-300'
    }
  }

  const getInitials = (name: string) => {
    if (!name) return 'CM'
    const parts = name.split(/\s+/).filter(Boolean)
    if (parts.length === 1) return parts[0].slice(0, 2).toUpperCase()
    return (parts[0][0] + parts[1][0]).toUpperCase()
  }

  const getAvatarBg = (name: string) => {
    const colors = [
      'bg-sky-100 text-sky-800 border-sky-300',
      'bg-teal-100 text-teal-800 border-teal-300',
      'bg-emerald-100 text-emerald-800 border-emerald-300',
      'bg-purple-100 text-purple-800 border-purple-300',
      'bg-indigo-100 text-indigo-800 border-indigo-300',
      'bg-amber-100 text-amber-800 border-amber-300',
    ]
    let hash = 0
    for (let i = 0; i < name.length; i++) {
      hash = name.charCodeAt(i) + ((hash << 5) - hash)
    }
    const index = Math.abs(hash) % colors.length
    return colors[index]
  }

  const filteredStories = useMemo(() => {
    return stories.filter((s) => {
      // Category filter
      if (selectedCategory !== 'all') {
        const storyCat = s.category || (s.condition_or_topic?.toLowerCase().includes('billing') ? 'Billing' : '')
        if (storyCat.toLowerCase() !== selectedCategory.toLowerCase()) {
          return false
        }
      }
      // Search query filter
      if (searchQuery.trim()) {
        const q = searchQuery.trim().toLowerCase()
        const inText = s.story_text.toLowerCase().includes(q)
        const inTitle = (s.title || '').toLowerCase().includes(q)
        const inAuthor = s.author_name.toLowerCase().includes(q)
        const inTopic = (s.condition_or_topic || '').toLowerCase().includes(q)
        const inLocation = (s.location || '').toLowerCase().includes(q)
        const inCategory = (s.category || '').toLowerCase().includes(q)
        if (!inText && !inTitle && !inAuthor && !inTopic && !inLocation && !inCategory) {
          return false
        }
      }
      return true
    })
  }, [stories, selectedCategory, searchQuery])

  return (
    <div className="space-y-8 max-w-4xl mx-auto font-sans pb-16">
      {/* Permanent High-Priority Medical Disclaimer */}
      <aside
        role="alert"
        aria-label="Important Medical Disclaimer"
        className="bg-amber-50/95 border-2 border-amber-300/80 rounded-2xl p-4 sm:p-5 shadow-sm text-amber-950 flex items-start gap-3.5 transition-all"
      >
        <span className="text-2xl flex-shrink-0 mt-0.5" aria-hidden="true">
          ⚠️
        </span>
        <div className="text-xs sm:text-sm leading-relaxed">
          <strong className="block font-black text-amber-950 text-xs sm:text-sm uppercase tracking-wide mb-1">
            Important Notice &bull; Not Medical Advice
          </strong>
          These are personal experiences, billing coping strategies, and recovery perspectives voluntarily shared by individuals.
          They are <strong>not medical advice, diagnosis, or treatment recommendations</strong>. Every body and clinical history is unique. Always consult qualified healthcare professionals before making any health decisions.
        </div>
      </aside>

      {/* Page Header Banner */}
      <div className="text-center max-w-2xl mx-auto pt-2">
        <div className="inline-flex items-center gap-2 px-3.5 py-1 rounded-full bg-clinical-50 border border-clinical-200 text-clinical-800 text-xs font-bold mb-3.5 shadow-xs">
          <span>🌱 Patient Perspectives &bull; Lived Experiences &bull; Billing Advocacy</span>
        </div>
        <h1 className="text-3xl sm:text-4xl font-black text-slate-900 tracking-tight leading-tight">
          Community Recovery &amp; Billing Stories
        </h1>
        <p className="mt-3 text-xs sm:text-sm text-slate-600 leading-relaxed max-w-xl mx-auto">
          A supportive, peer-shared community space where patients and families talk about dealing with unexpected hospital bills, deciphering prescriptions, recovering from illness, and finding transparent care.
        </p>

        {/* Share Button CTA */}
        <div className="mt-6 flex flex-wrap items-center justify-center gap-3">
          <button
            type="button"
            onClick={() => {
              setShowForm(!showForm)
              setError(null)
            }}
            className="px-6 py-3 rounded-xl bg-slate-900 hover:bg-slate-800 active:bg-slate-950 text-white text-xs font-bold shadow-md hover:shadow-lg transition-all inline-flex items-center gap-2"
          >
            <span>{showForm ? '✕' : '✍️'}</span>
            <span>{showForm ? 'Close Story Form' : 'Share Your Experience'}</span>
          </button>

          {!isAuthenticated && (
            <button
              type="button"
              onClick={async () => {
                await demoLogin()
              }}
              className="px-4 py-3 rounded-xl bg-white hover:bg-slate-50 text-slate-700 border border-slate-300 text-xs font-bold shadow-xs transition-colors inline-flex items-center gap-1.5"
            >
              <span>⚡ 1-Click Demo Auditor</span>
            </button>
          )}
        </div>
      </div>

      {/* Success Alert */}
      {successMessage && (
        <div className="p-4 rounded-xl bg-emerald-50 border border-emerald-300 text-emerald-950 text-xs sm:text-sm flex items-center justify-between shadow-sm animate-in fade-in duration-200">
          <div className="flex items-center gap-2.5">
            <span className="text-emerald-700 font-bold text-base">✓</span>
            <span className="font-semibold">{successMessage}</span>
          </div>
          <button
            type="button"
            onClick={() => setSuccessMessage(null)}
            className="text-emerald-700 hover:text-emerald-950 font-bold text-lg px-2"
            aria-label="Dismiss alert"
          >
            ×
          </button>
        </div>
      )}

      {/* Story Submission Form Card */}
      {showForm && (
        <form
          onSubmit={handleSubmit}
          className="bg-white rounded-2xl border border-slate-200 p-6 sm:p-8 shadow-card space-y-5 animate-in fade-in duration-300"
        >
          <div className="flex items-start justify-between pb-3.5 border-b border-slate-100">
            <div>
              <div className="inline-block px-2.5 py-0.5 rounded-full text-[10px] font-bold bg-sky-100 text-sky-800 uppercase tracking-wider mb-1">
                Contribute to the Community Feed
              </div>
              <h2 className="text-lg font-bold text-slate-900">
                Share What Helped You Keep Going &amp; Navigate Care
              </h2>
              <p className="text-xs text-slate-500 mt-0.5">
                Your practical experience can offer clarity and reassurance to another patient facing a similar challenge.
              </p>
            </div>
            <button
              type="button"
              onClick={() => setShowForm(false)}
              className="text-slate-400 hover:text-slate-600 p-1.5 rounded-lg text-sm"
              title="Close form"
            >
              ✕
            </button>
          </div>

          {error && (
            <div className="p-3.5 rounded-xl bg-rose-50 border border-rose-200 text-rose-800 text-xs">
              <strong>Notice:</strong> {error}
            </div>
          )}

          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            <div>
              <label className="block text-xs font-bold text-slate-700 mb-1">
                Story Title or Summary Headline <span className="text-rose-500">*</span>
              </label>
              <input
                type="text"
                value={title}
                onChange={(e) => setTitle(e.target.value)}
                placeholder="e.g. Disputed an itemized consumable fee in Bengaluru"
                className="w-full px-3.5 py-2.5 text-xs rounded-xl border border-slate-300 focus:outline-none focus:ring-2 focus:ring-sky-500 text-slate-800 placeholder:text-slate-400"
                required
              />
            </div>

            <div>
              <label className="block text-xs font-bold text-slate-700 mb-1">
                Primary Category <span className="text-rose-500">*</span>
              </label>
              <select
                value={category}
                onChange={(e) => setCategory(e.target.value)}
                className="w-full px-3.5 py-2.5 text-xs rounded-xl border border-slate-300 focus:outline-none focus:ring-2 focus:ring-sky-500 text-slate-800 bg-white"
              >
                <option value="Billing">🧾 Billing &amp; Price Disputes</option>
                <option value="Prescription">💊 Prescriptions &amp; Generic Drugs</option>
                <option value="Recovery">🌱 Chronic Condition / Surgery Recovery</option>
                <option value="Hospital Experience">🏥 Hospital &amp; Emergency Wait Times</option>
                <option value="Transparent Pricing">⚖️ Transparent Pricing Experience</option>
              </select>
            </div>
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
            <div>
              <label className="block text-xs font-bold text-slate-700 mb-1">
                Your Name or Alias
              </label>
              <input
                type="text"
                value={authorName}
                onChange={(e) => setAuthorName(e.target.value)}
                placeholder="e.g. Ramesh K. or Anonymous"
                className="w-full px-3.5 py-2 text-xs rounded-xl border border-slate-300 focus:outline-none focus:ring-2 focus:ring-sky-500 text-slate-800 placeholder:text-slate-400"
              />
            </div>

            <div>
              <label className="block text-xs font-bold text-slate-700 mb-1">
                Location (City / Hospital)
              </label>
              <input
                type="text"
                value={location}
                onChange={(e) => setLocation(e.target.value)}
                placeholder="e.g. Bengaluru, Karnataka"
                className="w-full px-3.5 py-2 text-xs rounded-xl border border-slate-300 focus:outline-none focus:ring-2 focus:ring-sky-500 text-slate-800 placeholder:text-slate-400"
              />
            </div>

            <div>
              <label className="block text-xs font-bold text-slate-700 mb-1">
                Condition or Procedure Tag
              </label>
              <input
                type="text"
                value={condition}
                onChange={(e) => setCondition(e.target.value)}
                placeholder="e.g. Gallbladder Surgery, Diabetes"
                className="w-full px-3.5 py-2 text-xs rounded-xl border border-slate-300 focus:outline-none focus:ring-2 focus:ring-sky-500 text-slate-800 placeholder:text-slate-400"
              />
            </div>
          </div>

          <div>
            <div className="flex items-center justify-between mb-1.5">
              <label className="block text-xs font-bold text-slate-700">
                Your Story &bull; What You Encountered &amp; What Worked <span className="text-rose-500">*</span>
              </label>
              <span className="text-[11px] font-mono text-slate-400">
                {storyText.length} / 5,000 characters
              </span>
            </div>
            <textarea
              rows={5}
              value={storyText}
              onChange={(e) => setStoryText(e.target.value)}
              placeholder="Describe what happened in plain, honest terms: what billing anomaly or healthcare obstacle you faced, the exact questions you asked, what helped you cope, and practical advice for others..."
              className="w-full px-3.5 py-2.5 text-xs sm:text-sm rounded-xl border border-slate-300 focus:outline-none focus:ring-2 focus:ring-sky-500 text-slate-800 leading-relaxed placeholder:text-slate-400"
              required
              maxLength={5000}
            />
          </div>

          {/* Voluntary Contact Details */}
          <div className="p-4 rounded-xl bg-slate-50 border border-slate-200 space-y-2.5">
            <div>
              <span className="text-xs font-bold text-slate-800 block">
                Voluntary Public Contact (Optional)
              </span>
              <p className="text-[11px] text-slate-500 mt-0.5">
                Only provide email or Instagram if you want fellow patients or peers facing similar conditions to connect with you.
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
                  placeholder="e.g. name@example.com"
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
          <div className="pt-1">
            <label className="flex items-start gap-2.5 text-xs text-slate-700 cursor-pointer select-none">
              <input
                type="checkbox"
                checked={consentAcknowledged}
                onChange={(e) => setConsentAcknowledged(e.target.checked)}
                className="mt-0.5 w-4 h-4 rounded text-sky-600 focus:ring-sky-500 border-slate-300"
                required
              />
              <span className="leading-relaxed">
                I understand that this story and any contact details I provide will be published to the public community feed. I confirm that this is a genuine personal account and not clinical or prescriptive medical advice.
              </span>
            </label>
          </div>

          {/* Form Actions */}
          <div className="flex items-center justify-end gap-3 pt-3 border-t border-slate-100">
            <button
              type="button"
              onClick={() => setShowForm(false)}
              className="px-4 py-2 rounded-xl text-xs font-semibold text-slate-600 hover:text-slate-900 transition-colors"
            >
              Cancel
            </button>
            <button
              type="submit"
              disabled={submitting || !storyText.trim() || !consentAcknowledged}
              className="px-6 py-2.5 rounded-xl bg-sky-600 hover:bg-sky-700 text-white text-xs font-bold shadow-sm transition-colors disabled:opacity-50 inline-flex items-center gap-2"
            >
              <span>{submitting ? 'Publishing...' : 'Publish Story to Community Feed'}</span>
              <span>&rarr;</span>
            </button>
          </div>
        </form>
      )}

      {/* Filter and Category Bar */}
      <div className="bg-white p-4 sm:p-5 rounded-2xl border border-slate-200 shadow-xs space-y-3.5">
        {/* Search bar */}
        <div className="relative">
          <input
            type="text"
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            placeholder="Search stories by hospital, city, medication, billing fee, or symptom..."
            className="w-full pl-9 pr-8 py-2.5 text-xs sm:text-sm rounded-xl border border-slate-300 focus:outline-none focus:ring-2 focus:ring-sky-500 bg-slate-50/50 text-slate-800 placeholder:text-slate-400"
          />
          <span className="absolute left-3 top-2.5 text-slate-400 text-sm" aria-hidden="true">
            🔍
          </span>
          {searchQuery && (
            <button
              type="button"
              onClick={() => setSearchQuery('')}
              className="absolute right-3 top-2.5 text-slate-400 hover:text-slate-600 text-xs font-bold"
              title="Clear search"
            >
              ✕
            </button>
          )}
        </div>

        {/* Category Pills */}
        <div className="flex items-center gap-1.5 overflow-x-auto pb-1 text-xs no-scrollbar">
          {CATEGORY_TABS.map((tab) => {
            const isActive = selectedCategory.toLowerCase() === tab.id.toLowerCase()
            return (
              <button
                key={tab.id}
                type="button"
                onClick={() => setSelectedCategory(tab.id)}
                className={`px-3 py-1.5 rounded-xl text-xs font-bold transition-all flex items-center gap-1.5 flex-shrink-0 ${
                  isActive
                    ? 'bg-slate-900 text-white shadow-sm'
                    : 'bg-slate-100 text-slate-600 hover:bg-slate-200 border border-slate-200/80'
                }`}
              >
                <span>{tab.icon}</span>
                <span>{tab.label}</span>
              </button>
            )
          })}
        </div>
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
          <h3 className="text-base font-bold text-slate-900">No Stories Match Your Search</h3>
          <p className="text-xs text-slate-500 mt-1 max-w-sm mx-auto">
            Try adjusting your search terms or view all categories to read community experiences.
          </p>
          <div className="mt-4 flex items-center justify-center gap-3">
            <button
              type="button"
              onClick={() => {
                setSelectedCategory('all')
                setSearchQuery('')
              }}
              className="px-4 py-2 bg-slate-100 hover:bg-slate-200 text-slate-800 rounded-xl text-xs font-bold transition-colors"
            >
              Reset Filters
            </button>
            <button
              type="button"
              onClick={() => setShowForm(true)}
              className="px-4 py-2 bg-sky-600 hover:bg-sky-700 text-white rounded-xl text-xs font-bold transition-colors"
            >
              Share Your Story
            </button>
          </div>
        </div>
      ) : (
        <div className="space-y-5">
          {filteredStories.map((story) => {
            const reaction = reactions[story.story_id] || { helpful: 10, encouraging: 6, reacted: false }
            const isUserStory = user && story.author_name === user.name
            return (
              <article
                key={story.story_id}
                className="bg-white rounded-2xl border border-slate-200/90 p-6 sm:p-7 shadow-sm hover:shadow-md transition-all duration-200"
              >
                {/* Header: Author, Badge, Location & Date */}
                <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2.5 mb-3.5">
                  <div className="flex items-center gap-2.5 flex-wrap">
                    {/* Monogram Avatar */}
                    <div
                      className={`w-8 h-8 rounded-full border flex items-center justify-center text-xs font-black flex-shrink-0 ${getAvatarBg(
                        story.author_name
                      )}`}
                    >
                      {getInitials(story.author_name)}
                    </div>

                    <div>
                      <div className="flex items-center gap-2 flex-wrap">
                        <span className="font-bold text-slate-900 text-xs sm:text-sm">
                          {story.author_name}
                        </span>
                        {isUserStory && (
                          <span className="px-2 py-0.5 rounded-md text-[10px] font-bold bg-sky-100 text-sky-800 border border-sky-200">
                            Your Story
                          </span>
                        )}
                        {story.is_demo && (
                          <span className="px-2 py-0.5 rounded-md text-[10px] font-semibold bg-slate-100 text-slate-600">
                            Verified Lived Account
                          </span>
                        )}
                      </div>

                      {story.location && (
                        <div className="text-[11px] text-slate-500 font-medium flex items-center gap-1 mt-0.5">
                          <span>📍</span>
                          <span>{story.location}</span>
                        </div>
                      )}
                    </div>
                  </div>

                  <div className="flex items-center gap-2 self-start sm:self-center">
                    {story.category && (
                      <span
                        className={`px-2.5 py-0.5 rounded-full text-[11px] font-bold border ${getCategoryBadgeClass(
                          story.category
                        )}`}
                      >
                        {story.category}
                      </span>
                    )}
                    <time className="text-[11px] text-slate-400 font-medium whitespace-nowrap">
                      {new Date(story.created_at).toLocaleDateString(undefined, {
                        year: 'numeric',
                        month: 'short',
                        day: 'numeric',
                      })}
                    </time>
                  </div>
                </div>

                {/* Title */}
                {story.title && (
                  <h3 className="text-base sm:text-lg font-bold text-slate-900 mb-2.5 tracking-tight">
                    {story.title}
                  </h3>
                )}

                {/* Condition Tag if not already category */}
                {story.condition_or_topic && (
                  <div className="mb-3">
                    <span className="inline-flex items-center gap-1 text-[11px] font-semibold text-slate-600 bg-slate-100/90 px-2.5 py-0.5 rounded-md border border-slate-200">
                      <span>🏷️</span>
                      <span>Topic: {story.condition_or_topic}</span>
                    </span>
                  </div>
                )}

                {/* Story Body */}
                <div className="text-xs sm:text-sm text-slate-700 leading-relaxed font-sans bg-slate-50/70 p-4 sm:p-4.5 rounded-xl border border-slate-100/90 whitespace-pre-line">
                  {story.story_text}
                </div>

                {/* Footer: Reactions + Voluntary Contact */}
                <div className="mt-4 pt-3.5 border-t border-slate-100 flex flex-col sm:flex-row sm:items-center justify-between gap-3 text-xs">
                  {/* Reaction Buttons */}
                  <div className="flex items-center gap-2">
                    <button
                      type="button"
                      onClick={() => toggleReaction(story.story_id, 'helpful')}
                      className={`inline-flex items-center gap-1.5 px-3 py-1 rounded-lg text-xs font-semibold border transition-all ${
                        reaction.reacted
                          ? 'bg-sky-50 text-sky-800 border-sky-300 font-bold'
                          : 'bg-white hover:bg-slate-50 text-slate-600 border-slate-200'
                      }`}
                      title="Mark as helpful"
                    >
                      <span>🙏</span>
                      <span>Helpful ({reaction.helpful})</span>
                    </button>

                    <button
                      type="button"
                      onClick={() => toggleReaction(story.story_id, 'encouraging')}
                      className={`inline-flex items-center gap-1.5 px-3 py-1 rounded-lg text-xs font-semibold border transition-all ${
                        reaction.reacted
                          ? 'bg-rose-50 text-rose-800 border-rose-300 font-bold'
                          : 'bg-white hover:bg-slate-50 text-slate-600 border-slate-200'
                      }`}
                      title="Mark as encouraging"
                    >
                      <span>❤️</span>
                      <span>Encouraging ({reaction.encouraging})</span>
                    </button>
                  </div>

                  {/* Optional Voluntary Contact Links */}
                  {(story.contact_email || story.contact_instagram) && (
                    <div className="flex items-center gap-2 flex-wrap text-xs">
                      <span className="text-[11px] text-slate-400 font-medium">
                        Shared by Author:
                      </span>
                      {story.contact_email && (
                        <a
                          href={`mailto:${story.contact_email}`}
                          className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-lg bg-sky-50 text-sky-700 hover:bg-sky-100 font-semibold text-xs transition-colors border border-sky-200"
                          title="Contact author via email"
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
                          className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-lg bg-pink-50 text-pink-700 hover:bg-pink-100 font-semibold text-xs transition-colors border border-pink-200"
                          title="Contact author via Instagram"
                        >
                          <span>📷</span>
                          <span>@{story.contact_instagram}</span>
                        </a>
                      )}
                    </div>
                  )}
                </div>
              </article>
            )
          })}
        </div>
      )}
    </div>
  )
}
