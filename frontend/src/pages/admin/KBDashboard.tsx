import { useEffect, useState, useCallback, useMemo } from 'react'
import { Tag, Typography, Spin, Button, message, Tooltip, Modal, Input, Skeleton } from 'antd'
import {
  TagsOutlined, ReloadOutlined, RightOutlined, EditOutlined, DownloadOutlined,
  SearchOutlined, ClearOutlined, FilePdfOutlined, FileTextOutlined,
  FileExcelOutlined, FileOutlined,
} from '@ant-design/icons'
import { useNavigate } from 'react-router-dom'
import { docsAPI } from '../../api/docs'
import dayjs from 'dayjs'

const { Text } = Typography

/* ============================================================
   Utils
   ============================================================ */

const fileTypeIcon: Record<string, React.ReactNode> = {
  pdf: <FilePdfOutlined style={{ color: '#e74c3c', fontSize: 13 }} />,
  docx: <FileTextOutlined style={{ color: '#2563eb', fontSize: 13 }} />,
  doc: <FileTextOutlined style={{ color: '#2563eb', fontSize: 13 }} />,
  txt: <FileTextOutlined style={{ color: '#6b7280', fontSize: 13 }} />,
  md: <FileTextOutlined style={{ color: '#6b7280', fontSize: 13 }} />,
  csv: <FileExcelOutlined style={{ color: '#16a34a', fontSize: 13 }} />,
  xlsx: <FileExcelOutlined style={{ color: '#16a34a', fontSize: 13 }} />,
  xls: <FileExcelOutlined style={{ color: '#16a34a', fontSize: 13 }} />,
}

function getCategoryColor(name: string): string {
  let hash = 0
  for (let i = 0; i < name.length; i++) {
    hash = name.charCodeAt(i) + ((hash << 5) - hash)
  }
  const hue = ((Math.abs(hash) % 360) + 360) % 360
  return `hsl(${hue}, 54%, 52%)`
}

function getCategoryBg(name: string): string {
  let hash = 0
  for (let i = 0; i < name.length; i++) {
    hash = name.charCodeAt(i) + ((hash << 5) - hash)
  }
  const hue = ((Math.abs(hash) % 360) + 360) % 360
  return `hsla(${hue}, 54%, 52%, 0.09)`
}

/* ============================================================
   Types
   ============================================================ */

interface DashboardData {
  total: number
  categories: Array<{
    name: string
    count: number
    items: Array<{
      id: string
      original_filename: string
      file_type: string
      summary: string | null
      tags: string[] | null
      created_at: string
    }>
  }>
}

interface DocItem {
  id: string
  original_filename: string
  file_type: string
  summary: string | null
  tags: string[] | null
  created_at: string
  categoryName: string
}

/* ============================================================
   Knowledge Spectrum
   ============================================================ */

function KnowledgeSpectrum({
  categories, total, selected, onSelect,
}: {
  categories: { name: string; count: number }[]
  total: number
  selected: string | null
  onSelect: (name: string | null) => void
}) {
  return (
    <div>
      <div style={{
        display: 'flex', width: '100%', height: 52,
        borderRadius: 8, overflow: 'hidden', background: '#e5e7eb',
      }}>
        {categories.map((cat) => {
          const fraction = cat.count / total
          const color = getCategoryColor(cat.name)
          const isActive = selected === cat.name
          let h = 0
          for (let i = 0; i < cat.name.length; i++) h = cat.name.charCodeAt(i) + ((h << 5) - h)
          const hue = ((Math.abs(h) % 360) + 360) % 360
          return (
            <Tooltip key={cat.name} title={`${cat.name} · ${cat.count} 篇 (${Math.round(fraction * 100)}%)`}>
              <div
                style={{
                  flex: Math.max(fraction, 0.06), height: '100%',
                  background: isActive ? color : `hsla(${hue}, 54%, 52%, 0.65)`,
                  display: 'flex', alignItems: 'center', justifyContent: 'center',
                  cursor: 'pointer', transition: 'all 0.2s', minWidth: 48,
                  opacity: isActive ? 1 : 0.8,
                  outline: isActive ? '2px solid #1a1a2e' : 'none', outlineOffset: -2,
                }}
                onClick={() => onSelect(isActive ? null : cat.name)}
                onMouseEnter={(e) => { (e.currentTarget as HTMLElement).style.opacity = '1' }}
                onMouseLeave={(e) => { (e.currentTarget as HTMLElement).style.opacity = isActive ? '1' : '0.8' }}
              >
                <span style={{
                  color: '#fff', fontSize: 12, fontWeight: 600,
                  textShadow: '0 1px 3px rgba(0,0,0,0.25)',
                  padding: '0 4px', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap',
                }}>
                  {cat.name}
                </span>
              </div>
            </Tooltip>
          )
        })}
      </div>
      <div style={{ display: 'flex', justifyContent: 'space-between', marginTop: 6, padding: '0 2px' }}>
        {categories.map((c) => {
          const pct = Math.round((c.count / total) * 100)
          const isActive = selected === c.name
          return (
            <Text key={c.name} style={{
              fontSize: 11, color: isActive ? '#1a1a2e' : '#6b7280',
              textAlign: 'center', flex: 1, fontWeight: isActive ? 600 : 400,
            }}>
              {c.count} 篇 · {pct}%
            </Text>
          )
        })}
      </div>
    </div>
  )
}

/* ============================================================
   Main Component
   ============================================================ */

const TAG_SHOW_LIMIT = 10

export default function KBDashboard() {
  const navigate = useNavigate()
  const [dashboard, setDashboard] = useState<DashboardData | null>(null)
  const [loading, setLoading] = useState(true)
  const [reclassifying, setReclassifying] = useState(false)

  /* ---- filters ---- */
  const [selectedCategory, setSelectedCategory] = useState<string | null>(null)
  const [selectedTags, setSelectedTags] = useState<Set<string>>(new Set())
  const [searchText, setSearchText] = useState('')
  const [showAllTags, setShowAllTags] = useState(false)

  /* ---- preview ---- */
  const [previewDoc, setPreviewDoc] = useState<{ id: string; filename: string } | null>(null)
  const [previewContent, setPreviewContent] = useState<{ chunks: Array<{ page: number; content: string }> } | null>(null)
  const [previewLoading, setPreviewLoading] = useState(false)

  /* ---- edit modal ---- */
  const [editingDoc, setEditingDoc] = useState<{
    id: string; original_filename: string; category: string; tags: string; summary: string
  } | null>(null)
  const [saving, setSaving] = useState(false)

  /* ---- data fetching ---- */

  const fetchDashboard = useCallback(async () => {
    try {
      const res = await docsAPI.dashboard()
      setDashboard(res.data)
    } catch {
      // handled
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => { fetchDashboard() }, [fetchDashboard])

  /* ---- auto-refresh on visibility change ---- */
  useEffect(() => {
    const onVisible = () => {
      if (document.visibilityState === 'visible') fetchDashboard()
    }
    document.addEventListener('visibilitychange', onVisible)
    return () => document.removeEventListener('visibilitychange', onVisible)
  }, [fetchDashboard])

  /* ---- derived data ---- */

  const { total, categories, allDocs, allTags, stats, tagFrequency } = useMemo(() => {
    if (!dashboard) return { total: 0, categories: [], allDocs: [], allTags: [], stats: [], tagFrequency: {} as Record<string, number> }
    const cats = dashboard.categories
    const docs = cats.flatMap((c) => c.items.map((doc) => ({ ...doc, categoryName: c.name })))

    // 统计标签频率
    const freq: Record<string, number> = {}
    docs.forEach((d) => d.tags?.forEach((t) => { freq[t] = (freq[t] || 0) + 1 }))
    const sortedTags = Object.entries(freq).sort((a, b) => b[1] - a[1]).map(([t]) => t)

    const sorted = [...docs].sort((a, b) => new Date(b.created_at).getTime() - new Date(a.created_at).getTime())

    return {
      total: dashboard.total,
      categories: cats,
      allDocs: docs,
      allTags: sortedTags,
      stats: [
        { label: '文档总数', value: dashboard.total },
        { label: '分类数量', value: cats.length },
        { label: '标签总数', value: sortedTags.length },
        { label: '最近更新', value: sorted.length > 0 ? dayjs(sorted[0].created_at).format('MM-DD') : '-' },
      ],
      tagFrequency: freq,
    }
  }, [dashboard])

  /* ---- filter logic ---- */

  const filteredDocs = useMemo(() => {
    let result = allDocs

    // 搜索：文档名、分类、标签
    if (searchText.trim()) {
      const q = searchText.trim().toLowerCase()
      result = result.filter((d) =>
        d.original_filename.toLowerCase().includes(q) ||
        d.categoryName.toLowerCase().includes(q) ||
        (d.tags && d.tags.some((t) => t.toLowerCase().includes(q)))
      )
    }

    // 按分类筛选
    if (selectedCategory) {
      result = result.filter((d) => d.categoryName === selectedCategory)
    }

    // 按标签筛选（多选，满足任一）
    if (selectedTags.size > 0) {
      result = result.filter((d) => d.tags && d.tags.some((t) => selectedTags.has(t)))
    }

    return [...result].sort((a, b) => new Date(b.created_at).getTime() - new Date(a.created_at).getTime())
  }, [allDocs, searchText, selectedCategory, selectedTags])

  /* ---- handlers ---- */

  const toggleTag = useCallback((tag: string) => {
    setSelectedTags((prev) => {
      const next = new Set(prev)
      if (next.has(tag)) next.delete(tag)
      else next.add(tag)
      return next
    })
  }, [])

  const clearFilters = useCallback(() => {
    setSelectedCategory(null)
    setSelectedTags(new Set())
    setSearchText('')
  }, [])

  const openPreview = useCallback(async (id: string, filename: string) => {
    setPreviewDoc({ id, filename })
    setPreviewContent(null)
    setPreviewLoading(true)
    try {
      const res = await docsAPI.preview(id)
      setPreviewContent(res.data)
    } catch {
      message.error('加载预览失败')
    } finally {
      setPreviewLoading(false)
    }
  }, [])

  const handleSaveMetadata = useCallback(async () => {
    if (!editingDoc) return
    setSaving(true)
    try {
      const tags = editingDoc.tags ? editingDoc.tags.split(/[,，、\s]+/).filter(Boolean) : []
      await docsAPI.updateMetadata(editingDoc.id, {
        original_filename: editingDoc.original_filename || undefined,
        category: editingDoc.category || undefined,
        tags: tags.length > 0 ? tags : undefined,
        summary: editingDoc.summary || undefined,
      })
      message.success('已更新')
      setEditingDoc(null)
      fetchDashboard()
    } catch (err: any) {
      const detail = err?.response?.data?.detail
      message.error(typeof detail === 'string' ? detail : '保存失败')
    } finally {
      setSaving(false)
    }
  }, [editingDoc, fetchDashboard])

  const handleReclassify = useCallback(async () => {
    setReclassifying(true)
    try {
      const res = await docsAPI.reclassify()
      message.success('分类已更新')
      fetchDashboard()
    } catch (err: any) {
      const detail = err?.response?.data?.detail
      message.error(typeof detail === 'string' ? detail : '重新分类失败')
    } finally {
      setReclassifying(false)
    }
  }, [fetchDashboard])

  const hasFilter = selectedCategory !== null || selectedTags.size > 0 || searchText.trim().length > 0

  const visibleTags = showAllTags ? allTags : allTags.slice(0, TAG_SHOW_LIMIT)
  const hiddenCount = allTags.length - TAG_SHOW_LIMIT

  /* ---- loading ---- */

  if (loading) {
    return <div style={{ display: 'flex', justifyContent: 'center', alignItems: 'center', height: 400 }}><Spin /></div>
  }

  if (!dashboard || dashboard.total === 0) {
    return (
      <div style={{ padding: 60, textAlign: 'center' }}>
        <Text style={{ color: '#6b7280', fontSize: 15 }}>
          暂无文档。去 <Text style={{ color: '#d97706', cursor: 'pointer' }} onClick={() => navigate('/admin/documents')}>知识库管理</Text> 上传文档
        </Text>
      </div>
    )
  }

  return (
    <div style={{ background: '#f8f6f3', minHeight: 'calc(100vh - 140px)' }}>
      <div style={{ maxWidth: 960, margin: '0 auto', padding: '32px 0' }}>
        {/* ================================================================
            标题
             ================================================================ */}
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: 20 }}>
          <div>
            <Text style={{ fontSize: 24, fontWeight: 700, color: '#1a1a2e', letterSpacing: '-0.5px' }}>知识库全景</Text>
            <div style={{ marginTop: 4 }}>
              <Text style={{ fontSize: 13, color: '#6b7280' }}>{total} 份文档 · {categories.length} 个分类 · {allTags.length} 个标签</Text>
            </div>
          </div>
          <Button size="small" icon={<TagsOutlined />} loading={reclassifying} onClick={handleReclassify}
            style={{ fontSize: 13, borderColor: '#d1d5db', color: '#1a1a2e' }}>AI 重新分类</Button>
        </div>

        {/* ================================================================
            Knowledge Spectrum
             ================================================================ */}
        <div style={{ marginBottom: 20 }}>
          <KnowledgeSpectrum categories={categories.map((c) => ({ name: c.name, count: c.count }))} total={total}
            selected={selectedCategory} onSelect={setSelectedCategory} />
        </div>

        {/* ================================================================
            统计卡片
             ================================================================ */}
        <div style={{
          display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: 1,
          background: '#e2e8f0', borderRadius: 8, overflow: 'hidden', marginBottom: 20,
        }}>
          {stats.map((s) => (
            <div key={s.label} style={{ background: '#fff', padding: '14px 20px', textAlign: 'center' }}>
              <Text style={{
                display: 'block', fontSize: 24, fontWeight: 700, color: '#1a1a2e',
                lineHeight: 1.2, fontVariantNumeric: 'tabular-nums',
              }}>{s.value}</Text>
              <Text style={{ fontSize: 12, color: '#6b7280', letterSpacing: '0.3px' }}>{s.label}</Text>
            </div>
          ))}
        </div>

        {/* ================================================================
            搜索框
             ================================================================ */}
        <div style={{ marginBottom: 14 }}>
          <Input
            prefix={<SearchOutlined style={{ color: '#9ca3af' }} />}
            placeholder="搜索文档名、分类、标签..."
            value={searchText}
            onChange={(e) => setSearchText(e.target.value)}
            allowClear
            style={{ borderRadius: 8, borderColor: '#d1d5db' }}
          />
        </div>

        {/* ================================================================
            分类筛选条
             ================================================================ */}
        <div style={{ marginBottom: 10 }}>
          <Text style={{ fontSize: 12, color: '#6b7280', marginRight: 8 }}>分类</Text>
          <span style={{ display: 'inline-flex', gap: 6, flexWrap: 'wrap' }}>
            <span onClick={() => setSelectedCategory(null)}
              style={{
                fontSize: 12, padding: '2px 10px', borderRadius: 12, cursor: 'pointer', lineHeight: '22px',
                background: !selectedCategory ? '#1a1a2e' : '#e5e7eb',
                color: !selectedCategory ? '#fff' : '#6b7280',
              }}>
              全部 {total}
            </span>
            {categories.map((c) => {
              const isActive = selectedCategory === c.name
              const color = getCategoryColor(c.name)
              return (
                <span key={c.name} onClick={() => setSelectedCategory(isActive ? null : c.name)}
                  style={{
                    fontSize: 12, padding: '2px 10px', borderRadius: 12, cursor: 'pointer', lineHeight: '22px',
                    background: isActive ? color : getCategoryBg(c.name),
                    color: isActive ? '#fff' : color, fontWeight: isActive ? 600 : 400,
                  }}>
                  {c.name} {c.count}
                </span>
              )
            })}
          </span>
        </div>

        {/* ================================================================
            标签筛选条（折叠）
             ================================================================ */}
        {allTags.length > 0 && (
          <div style={{ marginBottom: 16 }}>
            <Text style={{ fontSize: 12, color: '#6b7280', marginRight: 8 }}>标签</Text>
            <span style={{ display: 'inline-flex', gap: 6, flexWrap: 'wrap', alignItems: 'center' }}>
              {visibleTags.map((tag) => {
                const isActive = selectedTags.has(tag)
                return (
                  <span key={tag} onClick={() => toggleTag(tag)}
                    style={{
                      fontSize: 11, padding: '1px 8px', borderRadius: 10, cursor: 'pointer', lineHeight: '20px',
                      background: isActive ? '#d97706' : '#f3f4f6',
                      color: isActive ? '#fff' : '#6b7280', fontWeight: isActive ? 500 : 400,
                      transition: 'all 0.15s',
                    }}>
                    {tag}
                  </span>
                )
              })}
              {!showAllTags && hiddenCount > 0 && (
                <span onClick={() => setShowAllTags(true)}
                  style={{
                    fontSize: 11, padding: '1px 8px', borderRadius: 10, cursor: 'pointer', lineHeight: '20px',
                    color: '#d97706', background: '#fef3c7', fontWeight: 500,
                  }}>
                  +{hiddenCount} 更多
                </span>
              )}
              {showAllTags && (
                <span onClick={() => setShowAllTags(false)}
                  style={{
                    fontSize: 11, padding: '1px 8px', borderRadius: 10, cursor: 'pointer', lineHeight: '20px',
                    color: '#6b7280', background: '#e5e7eb',
                  }}>
                  收起
                </span>
              )}
            </span>
          </div>
        )}

        {/* ================================================================
            筛选提示
             ================================================================ */}
        {hasFilter && (
          <div style={{ marginBottom: 12, display: 'flex', alignItems: 'center', gap: 8 }}>
            <Text style={{ fontSize: 12, color: '#6b7280' }}>筛选结果：{filteredDocs.length} 篇</Text>
            <Button type="text" size="small" icon={<ClearOutlined style={{ fontSize: 11 }} />}
              onClick={clearFilters} style={{ fontSize: 11, color: '#6b7280', height: 20 }}>清除筛选</Button>
          </div>
        )}

        {/* ================================================================
            文档列表
             ================================================================ */}
        <div style={{ background: '#fff', borderRadius: 8, overflow: 'hidden' }}>
          <div style={{
            display: 'flex', justifyContent: 'space-between', alignItems: 'center',
            padding: '12px 16px', borderBottom: '1px solid #f3f0eb',
          }}>
            <Text style={{ fontSize: 15, fontWeight: 600, color: '#1a1a2e' }}>
              {hasFilter ? '筛选结果' : '全部文档'}
            </Text>
            <Text style={{ fontSize: 13, color: '#d97706', cursor: 'pointer' }} onClick={() => navigate('/admin/documents')}>
              管理全部 <RightOutlined style={{ fontSize: 10 }} />
            </Text>
          </div>

          {filteredDocs.length === 0 ? (
            <div style={{ padding: '32px 16px', textAlign: 'center' }}>
              <Text style={{ color: '#6b7280', fontSize: 13 }}>没有匹配的文档</Text>
            </div>
          ) : (
            filteredDocs.map((doc, i) => (
              <div key={doc.id} style={{
                display: 'flex', alignItems: 'center', gap: 10, padding: '10px 16px',
                borderBottom: i < filteredDocs.length - 1 ? '1px solid #f3f0eb' : 'none',
              }}>
                <span style={{ flexShrink: 0, width: 16, textAlign: 'center' }}>
                  {fileTypeIcon[doc.file_type] || <FileOutlined style={{ fontSize: 13 }} />}
                </span>

                <Text
                  style={{
                    flex: 1, minWidth: 0, fontSize: 13, color: '#2563eb',
                    overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap',
                    cursor: 'pointer',
                  }}
                  title={doc.original_filename}
                  onClick={() => openPreview(doc.id, doc.original_filename)}
                >
                  {doc.original_filename}
                </Text>

                <span style={{
                  flexShrink: 0, fontSize: 11, padding: '0 8px', borderRadius: 10, lineHeight: '20px',
                  color: getCategoryColor(doc.categoryName), background: getCategoryBg(doc.categoryName),
                  marginRight: 4,
                }}>
                  {doc.categoryName}
                </span>

                {doc.tags && doc.tags.length > 0 && (
                  <span style={{ flexShrink: 0, display: 'flex', gap: 4, maxWidth: 160, overflow: 'hidden' }}>
                    {doc.tags.slice(0, 2).map((t) => (
                      <span key={t} style={{
                        fontSize: 11, color: '#6b7280', background: '#f3f4f6',
                        padding: '0 6px', borderRadius: 4, whiteSpace: 'nowrap',
                      }}>{t}</span>
                    ))}
                    {doc.tags.length > 2 && <span style={{ fontSize: 11, color: '#9ca3af' }}>+{doc.tags.length - 2}</span>}
                  </span>
                )}

                <Text style={{ flexShrink: 0, fontSize: 11, color: '#9ca3af', width: 44, textAlign: 'right' }}>
                  {dayjs(doc.created_at).format('MM-DD')}
                </Text>

                <Button type="text" size="small" icon={<DownloadOutlined style={{ fontSize: 11, color: '#9ca3af' }} />}
                  style={{ flexShrink: 0, width: 20, height: 20 }}
                  onClick={() => docsAPI.download(doc.id, doc.original_filename)} />

                <Button type="text" size="small" icon={<EditOutlined style={{ fontSize: 11, color: '#9ca3af' }} />}
                  style={{ flexShrink: 0, width: 20, height: 20 }}
                  onClick={() => setEditingDoc({
                    id: doc.id,
                    original_filename: doc.original_filename,
                    category: doc.categoryName,
                    tags: (doc.tags || []).join(', '),
                    summary: doc.summary || '',
                  })} />
              </div>
            ))
          )}
        </div>
      </div>

      {/* ================================================================
          预览弹窗
           ================================================================ */}
      <Modal title={previewDoc?.filename || '文档预览'} open={!!previewDoc}
        onCancel={() => { setPreviewDoc(null); setPreviewContent(null) }}
        footer={null} width={640}>
        {previewLoading ? (
          <div style={{ padding: '20px 0' }}><Skeleton active paragraph={{ rows: 6 }} /></div>
        ) : previewContent ? (
          <div style={{ maxHeight: 480, overflow: 'auto' }}>
            {previewContent.chunks.map((chunk, i) => (
              <div key={i} style={{
                padding: 12, marginBottom: 8, background: '#f8fafc', borderRadius: 6,
                borderLeft: '3px solid #e2e8f0', fontSize: 13, lineHeight: 1.6,
                color: '#334155', whiteSpace: 'pre-wrap',
              }}>
                {chunk.content}
              </div>
            ))}
          </div>
        ) : null}
      </Modal>

      {/* ================================================================
          编辑弹窗
           ================================================================ */}
      <Modal title="编辑文档" open={!!editingDoc} onCancel={() => setEditingDoc(null)}
        onOk={handleSaveMetadata} confirmLoading={saving} okText="保存" cancelText="取消" width={480}>
        {editingDoc && (
          <div style={{ display: 'flex', flexDirection: 'column', gap: 14 }}>
            <div>
              <Text style={{ fontSize: 13, fontWeight: 600, color: '#1a1a2e', display: 'block', marginBottom: 4 }}>
                文件名
              </Text>
              <Input value={editingDoc.original_filename}
                onChange={(e) => setEditingDoc({ ...editingDoc, original_filename: e.target.value })}
                placeholder="文档名称" />
            </div>
            <div>
              <Text style={{ fontSize: 13, fontWeight: 600, color: '#1a1a2e', display: 'block', marginBottom: 4 }}>
                分类
              </Text>
              <Input value={editingDoc.category}
                onChange={(e) => setEditingDoc({ ...editingDoc, category: e.target.value })}
                placeholder="输入分类名称，如：个人简历、学术论文..." />
            </div>
            <div>
              <Text style={{ fontSize: 13, fontWeight: 600, color: '#1a1a2e', display: 'block', marginBottom: 4 }}>
                标签（用逗号分隔）
              </Text>
              <Input value={editingDoc.tags}
                onChange={(e) => setEditingDoc({ ...editingDoc, tags: e.target.value })}
                placeholder="如：AI开发, 深度学习, 计算机视觉" />
            </div>
            <div>
              <Text style={{ fontSize: 13, fontWeight: 600, color: '#1a1a2e', display: 'block', marginBottom: 4 }}>
                摘要
              </Text>
              <Input.TextArea value={editingDoc.summary}
                onChange={(e) => setEditingDoc({ ...editingDoc, summary: e.target.value })}
                rows={3} placeholder="一句话概括文档内容" />
            </div>
          </div>
        )}
      </Modal>
    </div>
  )
}