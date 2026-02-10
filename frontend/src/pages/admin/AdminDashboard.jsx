import { useCallback, useEffect, useMemo, useState } from 'react'
import { Layer, Marker, Source } from 'react-map-gl'
import {
  Activity,
  Building2,
  Database,
  Globe,
  LogOut,
  PlusCircle,
  Settings,
  Shield,
  Tags,
  Trash2,
} from 'lucide-react'
import { useNavigate } from 'react-router-dom'
import { authService } from '../../services/auth'
import api from '../../services/api'
import { BaseMap } from '../../components/BaseMap'
import { MapControls } from '../../components/MapControls'
import { useAutoRefresh } from '../../hooks/useAutoRefresh'

const tabButton = (active) =>
  `w-full flex items-center gap-3 p-4 rounded-2xl font-bold transition-all ${
    active
      ? 'bg-white text-slate-950 shadow-lg'
      : 'text-slate-500 hover:text-white hover:bg-white/5'
  }`

export default function AdminDashboard() {
  const navigate = useNavigate()
  const [activeTab, setActiveTab] = useState('overview')
  const [stats, setStats] = useState(null)
  const [audits, setAudits] = useState([])
  const [authorities, setAuthorities] = useState([])
  const [issueTypes, setIssueTypes] = useState([])
  const [lastRefresh, setLastRefresh] = useState(new Date())

  const [authorityName, setAuthorityName] = useState('')
  const [authorityAdminEmail, setAuthorityAdminEmail] = useState('')
  const [authorityZoneName, setAuthorityZoneName] = useState('')
  const [polygonPoints, setPolygonPoints] = useState([])

  const [issueTypeName, setIssueTypeName] = useState('')
  const [issueTypePriority, setIssueTypePriority] = useState('P3')
  const [issueTypeSla, setIssueTypeSla] = useState(7)

  const [manualCategoryId, setManualCategoryId] = useState('')
  const [manualLat, setManualLat] = useState('')
  const [manualLng, setManualLng] = useState('')
  const [manualAddress, setManualAddress] = useState('')

  const refreshAll = useCallback(async () => {
    const [statsRes, authoritiesRes, issueTypesRes] = await Promise.all([
      api.get('/analytics/stats'),
      api.get('/admin/authorities').catch(() => ({ data: [] })),
      api.get('/admin/issue-types').catch(() => ({ data: [] })),
    ])
    setStats(statsRes.data)
    setAuthorities(authoritiesRes.data)
    setIssueTypes(issueTypesRes.data)
    setLastRefresh(new Date())
  }, [])

  const refreshAudits = useCallback(async () => {
    const auditRes = await api.get('/analytics/audit-all').catch(() => ({ data: [] }))
    setAudits(auditRes.data)
    setLastRefresh(new Date())
  }, [])

  useEffect(() => {
    refreshAll().catch(() => undefined)
  }, [refreshAll])

  useEffect(() => {
    if (activeTab === 'logs') {
      refreshAudits().catch(() => undefined)
    }
  }, [activeTab, refreshAudits])

  useAutoRefresh(
    () => {
      if (activeTab === 'logs') {
        Promise.all([refreshAll(), refreshAudits()]).catch(() => undefined)
        return
      }
      refreshAll().catch(() => undefined)
    },
    { intervalMs: 30000, runOnMount: false }
  )

  const polygonGeoJson = useMemo(() => {
    if (polygonPoints.length < 3) return null
    const closed = [...polygonPoints, polygonPoints[0]]
    return {
      type: 'FeatureCollection',
      features: [
        {
          type: 'Feature',
          geometry: {
            type: 'Polygon',
            coordinates: [closed],
          },
        },
      ],
    }
  }, [polygonPoints])

  const createAuthority = async () => {
    if (!authorityName || !authorityAdminEmail || polygonPoints.length < 3) {
      alert('Name, admin email and polygon points are required')
      return
    }
    await api.post('/admin/authorities', {
      name: authorityName,
      admin_email: authorityAdminEmail,
      zone_name: authorityZoneName || undefined,
      jurisdiction_points: polygonPoints,
    })
    setAuthorityName('')
    setAuthorityAdminEmail('')
    setAuthorityZoneName('')
    setPolygonPoints([])
    refreshAll()
  }

  const createIssueType = async () => {
    if (!issueTypeName) return
    await api.post('/admin/issue-types', {
      name: issueTypeName,
      default_priority: issueTypePriority,
      expected_sla_days: Number(issueTypeSla),
    })
    setIssueTypeName('')
    refreshAll()
  }

  const deactivateIssueType = async (categoryId) => {
    await api.delete(`/admin/issue-types/${categoryId}`)
    refreshAll()
  }

  const updateIssueType = async (category) => {
    const nextName = window.prompt('Updated issue type name', category.name)
    if (!nextName || nextName === category.name) return
    await api.put(`/admin/issue-types/${category.id}`, { name: nextName })
    refreshAll()
  }

  const createManualIssue = async () => {
    if (!manualCategoryId || !manualLat || !manualLng) {
      alert('Category and coordinates are required')
      return
    }
    await api.post('/admin/manual-issues', {
      category_id: manualCategoryId,
      lat: Number(manualLat),
      lng: Number(manualLng),
      address: manualAddress || null,
    })
    setManualAddress('')
    alert('Manual issue created')
  }

  return (
    <div className="flex h-screen bg-[#F8FAFC]">
      <aside className="w-80 bg-slate-950 text-white flex flex-col p-8">
        <div className="flex items-center gap-4 mb-10">
          <div className="w-12 h-12 bg-white rounded-2xl flex items-center justify-center text-slate-950">
            <Shield size={26} />
          </div>
          <h1 className="text-xl font-black">MARG IT Admin</h1>
        </div>

        <nav className="flex-1 space-y-3">
          <button onClick={() => setActiveTab('overview')} className={tabButton(activeTab === 'overview')}>
            <Activity size={18} /> Overview
          </button>
          <button onClick={() => navigate('/analytics')} className={tabButton(false)}>
            <Globe size={18} /> Full Analytics
          </button>
          <button onClick={() => setActiveTab('authorities')} className={tabButton(activeTab === 'authorities')}>
            <Building2 size={18} /> Authorities
          </button>
          <button onClick={() => setActiveTab('issueTypes')} className={tabButton(activeTab === 'issueTypes')}>
            <Tags size={18} /> Issue Types
          </button>
          <button onClick={() => setActiveTab('manualIssues')} className={tabButton(activeTab === 'manualIssues')}>
            <PlusCircle size={18} /> Manual Issue
          </button>
          <button onClick={() => setActiveTab('logs')} className={tabButton(activeTab === 'logs')}>
            <Database size={18} /> Audit Logs
          </button>
        </nav>

        <button
          onClick={() => authService.logout()}
          className="w-full flex items-center gap-3 p-4 mt-8 text-rose-400 font-bold hover:bg-rose-500/10 rounded-2xl"
        >
          <LogOut size={18} /> Exit
        </button>
      </aside>

      <main className="flex-1 p-10 overflow-auto space-y-6">
        <div className="text-xs font-bold text-slate-400">Synced {lastRefresh.toLocaleTimeString()}</div>
        {activeTab === 'overview' && (
          <div className="grid grid-cols-1 md:grid-cols-4 gap-6">
            <StatCard label="Reported" value={stats?.summary?.reported || 0} />
            <StatCard label="Workers" value={stats?.summary?.workers || 0} />
            <StatCard label="Resolved" value={stats?.summary?.resolved || 0} />
            <StatCard label="Authorities" value={authorities.length} />
          </div>
        )}

        {activeTab === 'authorities' && (
          <div className="space-y-6">
            <section className="bg-white rounded-3xl border border-slate-100 p-6 space-y-4 shadow-xl">
              <h3 className="text-lg font-black">Register Government Authority</h3>
              <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
                <input className="p-3 border rounded-xl" placeholder="Authority Name" value={authorityName} onChange={(e) => setAuthorityName(e.target.value)} />
                <input className="p-3 border rounded-xl" placeholder="Admin Email" value={authorityAdminEmail} onChange={(e) => setAuthorityAdminEmail(e.target.value)} />
                <input className="p-3 border rounded-xl" placeholder="Zone Name (optional)" value={authorityZoneName} onChange={(e) => setAuthorityZoneName(e.target.value)} />
              </div>
              <p className="text-xs text-slate-500">Click on map to add polygon points for jurisdiction. Minimum 3 points required.</p>
              <div className="h-[360px] rounded-2xl overflow-hidden border">
                <BaseMap
                  initialViewState={{ longitude: 78.4867, latitude: 17.385, zoom: 10 }}
                  onClick={(e) => {
                    const { lng, lat } = e.lngLat
                    setPolygonPoints((prev) => [...prev, [lng, lat]])
                  }}
                >
                  {polygonPoints.map((point, idx) => (
                    <Marker key={`${point[0]}-${point[1]}-${idx}`} longitude={point[0]} latitude={point[1]} color="#2563eb" />
                  ))}
                  {polygonGeoJson && (
                    <Source id="authority-polygon" type="geojson" data={polygonGeoJson}>
                      <Layer id="authority-fill" type="fill" paint={{ 'fill-color': '#2563eb', 'fill-opacity': 0.2 }} />
                      <Layer id="authority-line" type="line" paint={{ 'line-color': '#1d4ed8', 'line-width': 2 }} />
                    </Source>
                  )}
                  <MapControls />
                </BaseMap>
              </div>
              <div className="flex gap-3">
                <button className="px-4 py-2 rounded-xl bg-slate-100 font-bold" onClick={() => setPolygonPoints([])}>
                  Clear Polygon
                </button>
                <button className="px-4 py-2 rounded-xl bg-blue-600 text-white font-bold" onClick={createAuthority}>
                  Create Authority
                </button>
              </div>
            </section>

            <section className="bg-white rounded-3xl border border-slate-100 p-6 shadow-xl">
              <h3 className="text-lg font-black mb-4">Government Authorities</h3>
              <div className="overflow-x-auto">
                <table className="w-full text-sm">
                  <thead className="text-left text-slate-400 uppercase text-xs">
                    <tr>
                      <th className="py-2">Name</th>
                      <th className="py-2">Zone</th>
                      <th className="py-2">Admins</th>
                      <th className="py-2">Workers</th>
                    </tr>
                  </thead>
                  <tbody>
                    {authorities.map((authority) => (
                      <tr key={authority.org_id} className="border-t">
                        <td className="py-2 font-bold">{authority.name}</td>
                        <td className="py-2">{authority.zone_name}</td>
                        <td className="py-2">{authority.admin_count}</td>
                        <td className="py-2">{authority.worker_count}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </section>
          </div>
        )}

        {activeTab === 'issueTypes' && (
          <div className="space-y-6">
            <section className="bg-white rounded-3xl border border-slate-100 p-6 shadow-xl space-y-3">
              <h3 className="text-lg font-black">Create Issue Type</h3>
              <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
                <input className="p-3 border rounded-xl" placeholder="Name" value={issueTypeName} onChange={(e) => setIssueTypeName(e.target.value)} />
                <select className="p-3 border rounded-xl" value={issueTypePriority} onChange={(e) => setIssueTypePriority(e.target.value)}>
                  {['P1', 'P2', 'P3', 'P4'].map((p) => <option key={p}>{p}</option>)}
                </select>
                <input className="p-3 border rounded-xl" type="number" min="1" value={issueTypeSla} onChange={(e) => setIssueTypeSla(e.target.value)} />
              </div>
              <button className="px-4 py-2 rounded-xl bg-blue-600 text-white font-bold" onClick={createIssueType}>Create</button>
            </section>

            <section className="bg-white rounded-3xl border border-slate-100 p-6 shadow-xl">
              <h3 className="text-lg font-black mb-4">Issue Types</h3>
              <div className="space-y-2">
                {issueTypes.map((category) => (
                  <div key={category.id} className="flex items-center justify-between border rounded-xl p-3">
                    <div>
                      <p className="font-bold text-slate-900">{category.name}</p>
                      <p className="text-xs text-slate-500">Priority {category.default_priority} • SLA {category.expected_sla_days} days</p>
                    </div>
                    <div className="flex items-center gap-2">
                      <button
                        onClick={() => updateIssueType(category)}
                        className="inline-flex items-center gap-1 px-3 py-1 text-xs rounded-lg bg-slate-100 text-slate-700 font-bold"
                      >
                        <Settings size={14} /> Update
                      </button>
                      <button
                        onClick={() => deactivateIssueType(category.id)}
                        className="inline-flex items-center gap-1 px-3 py-1 text-xs rounded-lg bg-rose-50 text-rose-600 font-bold"
                      >
                        <Trash2 size={14} /> Deactivate
                      </button>
                    </div>
                  </div>
                ))}
              </div>
            </section>
          </div>
        )}

        {activeTab === 'manualIssues' && (
          <section className="bg-white rounded-3xl border border-slate-100 p-6 shadow-xl space-y-4 max-w-3xl">
            <h3 className="text-lg font-black">Manual Issue Creation</h3>
            <select className="w-full p-3 border rounded-xl" value={manualCategoryId} onChange={(e) => setManualCategoryId(e.target.value)}>
              <option value="">Select issue type</option>
              {issueTypes.filter((type) => type.is_active).map((type) => (
                <option key={type.id} value={type.id}>{type.name}</option>
              ))}
            </select>
            <div className="grid grid-cols-2 gap-3">
              <input className="p-3 border rounded-xl" placeholder="Latitude" value={manualLat} onChange={(e) => setManualLat(e.target.value)} />
              <input className="p-3 border rounded-xl" placeholder="Longitude" value={manualLng} onChange={(e) => setManualLng(e.target.value)} />
            </div>
            <input className="w-full p-3 border rounded-xl" placeholder="Address" value={manualAddress} onChange={(e) => setManualAddress(e.target.value)} />
            <button className="px-4 py-2 rounded-xl bg-blue-600 text-white font-bold" onClick={createManualIssue}>Create Manual Issue</button>
          </section>
        )}

        {activeTab === 'logs' && (
          <section className="bg-white rounded-3xl border border-slate-100 p-6 shadow-xl">
            <h3 className="text-lg font-black mb-4">Entire Audit Trail</h3>
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead className="text-left text-slate-400 uppercase text-xs">
                  <tr>
                    <th className="py-2">Time</th>
                    <th className="py-2">Action</th>
                    <th className="py-2">Entity</th>
                    <th className="py-2">Actor</th>
                    <th className="py-2">Change</th>
                  </tr>
                </thead>
                <tbody>
                  {audits.map((log) => (
                    <tr key={log.id} className="border-t">
                      <td className="py-2">{new Date(log.created_at).toLocaleString()}</td>
                      <td className="py-2 font-bold">{log.action}</td>
                      <td className="py-2">{log.entity_type}</td>
                      <td className="py-2">{String(log.actor_id).slice(0, 8)}</td>
                      <td className="py-2 text-xs text-slate-500">{log.old_value || 'NA'} {' -> '} {log.new_value || 'NA'}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </section>
        )}
      </main>
    </div>
  )
}

function StatCard({ label, value }) {
  return (
    <div className="bg-white rounded-3xl p-6 border border-slate-100 shadow-lg">
      <p className="text-xs font-bold uppercase tracking-wider text-slate-400">{label}</p>
      <p className="text-3xl font-black text-slate-900 mt-2">{value}</p>
    </div>
  )
}
