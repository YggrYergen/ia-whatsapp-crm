'use client'

import React, { useState, useEffect, useCallback } from 'react'
import { Image as ImageIcon, FileText, Download, Headphones, Video, MapPin, Smile, AlertCircle, Loader2 } from 'lucide-react'

interface MediaMetadata {
    media_id?: string
    mime_type?: string
    sha256?: string
    caption?: string
    filename?: string
    animated?: boolean
    download_status?: string
    storage_path?: string
    file_size?: number
    error?: string
    // Location fields
    latitude?: number
    longitude?: number
    name?: string
    address?: string
    // Reaction fields
    reacted_message_id?: string
    emoji?: string
}

interface MediaBubbleProps {
    messageType: string
    mediaMetadata: MediaMetadata | null
    tenantId: string
}

const BACKEND_URL = process.env.NEXT_PUBLIC_BACKEND_URL || 'https://ia-backend-prod-ftyhfnvyla-uc.a.run.app'

export default function MediaBubble({ messageType, mediaMetadata, tenantId }: MediaBubbleProps) {
    const [signedUrl, setSignedUrl] = useState<string | null>(null)
    const [loading, setLoading] = useState(false)
    const [error, setError] = useState<string | null>(null)
    const [imageExpanded, setImageExpanded] = useState(false)

    const fetchSignedUrl = useCallback(async (storagePath: string) => {
        setLoading(true)
        setError(null)
        try {
            const res = await fetch(
                `${BACKEND_URL}/api/media/signed-url?path=${encodeURIComponent(storagePath)}&tenant_id=${encodeURIComponent(tenantId)}`
            )
            if (!res.ok) {
                throw new Error(`HTTP ${res.status}`)
            }
            const data = await res.json()
            if (data.signed_url) {
                setSignedUrl(data.signed_url)
            } else {
                setError('No URL returned')
            }
        } catch (err: any) {
            console.error('[MediaBubble] Signed URL fetch failed:', err)
            setError(err.message || 'Error loading media')
        } finally {
            setLoading(false)
        }
    }, [tenantId])

    useEffect(() => {
        if (mediaMetadata?.storage_path && mediaMetadata.download_status === 'completed') {
            fetchSignedUrl(mediaMetadata.storage_path)
        }
    }, [mediaMetadata?.storage_path, mediaMetadata?.download_status, fetchSignedUrl])

    // ─── Download pending state ───
    if (mediaMetadata?.download_status === 'pending') {
        return (
            <div className="flex items-center gap-2 py-2 px-3 rounded-lg bg-slate-50 border border-slate-200 text-slate-500 text-xs">
                <Loader2 className="w-4 h-4 animate-spin" />
                <span>Descargando {messageType === 'image' ? 'imagen' : messageType === 'document' ? 'documento' : messageType === 'audio' ? 'audio' : messageType === 'video' ? 'video' : 'archivo'}...</span>
            </div>
        )
    }

    // ─── Download failed state ───
    if (mediaMetadata?.download_status === 'failed') {
        return (
            <div className="flex items-center gap-2 py-2 px-3 rounded-lg bg-red-50 border border-red-200 text-red-600 text-xs">
                <AlertCircle className="w-4 h-4" />
                <span>Error al descargar el archivo</span>
            </div>
        )
    }

    // ─── Location ───
    if (messageType === 'location' && mediaMetadata) {
        const { latitude, longitude, name, address } = mediaMetadata
        const mapUrl = `https://www.google.com/maps?q=${latitude},${longitude}`
        return (
            <a
                href={mapUrl}
                target="_blank"
                rel="noopener noreferrer"
                className="flex items-center gap-2 py-2 px-3 rounded-lg bg-blue-50 border border-blue-200 text-blue-700 text-xs hover:bg-blue-100 transition-colors"
            >
                <MapPin className="w-4 h-4 flex-shrink-0" />
                <div className="min-w-0">
                    <div className="font-medium truncate">{name || 'Ubicación compartida'}</div>
                    {address && <div className="text-blue-500 truncate">{address}</div>}
                </div>
            </a>
        )
    }

    // ─── Reaction ───
    if (messageType === 'reaction' && mediaMetadata?.emoji) {
        return (
            <div className="flex items-center gap-1.5 py-1 px-2 rounded-full bg-slate-50 border border-slate-200 text-sm w-fit">
                <Smile className="w-3.5 h-3.5 text-slate-400" />
                <span className="text-lg">{mediaMetadata.emoji}</span>
            </div>
        )
    }

    // ─── Sticker ───
    if (messageType === 'sticker') {
        return (
            <div className="flex items-center gap-2 py-2 px-3 rounded-lg bg-yellow-50 border border-yellow-200 text-yellow-700 text-xs">
                <span className="text-lg">🎭</span>
                <span>Sticker</span>
            </div>
        )
    }

    // ─── Unsupported ───
    if (messageType === 'unsupported') {
        return (
            <div className="flex items-center gap-2 py-2 px-3 rounded-lg bg-slate-50 border border-slate-200 text-slate-400 text-xs italic">
                <AlertCircle className="w-4 h-4" />
                <span>Tipo de mensaje no soportado</span>
            </div>
        )
    }

    // ─── Loading signed URL ───
    if (loading) {
        return (
            <div className="flex items-center gap-2 py-2 px-3 rounded-lg bg-slate-50 border border-slate-200 text-slate-500 text-xs">
                <Loader2 className="w-4 h-4 animate-spin" />
                <span>Cargando...</span>
            </div>
        )
    }

    // ─── No storage path yet (still downloading or missing) ───
    if (!signedUrl && !error) {
        const icons: Record<string, React.ReactNode> = {
            image: <ImageIcon className="w-4 h-4" />,
            document: <FileText className="w-4 h-4" />,
            audio: <Headphones className="w-4 h-4" />,
            video: <Video className="w-4 h-4" />,
        }
        return (
            <div className="flex items-center gap-2 py-2 px-3 rounded-lg bg-slate-50 border border-slate-200 text-slate-400 text-xs">
                {icons[messageType] || <ImageIcon className="w-4 h-4" />}
                <span>{messageType === 'image' ? 'Imagen' : messageType === 'document' ? 'Documento' : messageType === 'audio' ? 'Audio' : 'Video'}</span>
            </div>
        )
    }

    // ─── Error state ───
    if (error) {
        return (
            <div className="flex items-center gap-2 py-2 px-3 rounded-lg bg-red-50 border border-red-200 text-red-500 text-xs">
                <AlertCircle className="w-4 h-4" />
                <span>Error: {error}</span>
            </div>
        )
    }

    // ─── IMAGE ───
    if (messageType === 'image' && signedUrl) {
        return (
            <div className="mb-1.5">
                <img
                    src={signedUrl}
                    alt={mediaMetadata?.caption || 'Imagen compartida'}
                    className="max-w-full max-h-[300px] rounded-lg cursor-pointer hover:opacity-90 transition-opacity object-contain"
                    loading="lazy"
                    onClick={() => setImageExpanded(true)}
                />
                {/* Lightbox */}
                {imageExpanded && (
                    <div
                        className="fixed inset-0 z-[9999] bg-black/80 flex items-center justify-center p-4 cursor-pointer"
                        onClick={() => setImageExpanded(false)}
                    >
                        <img
                            src={signedUrl}
                            alt={mediaMetadata?.caption || 'Imagen compartida'}
                            className="max-w-full max-h-full object-contain rounded-lg shadow-2xl"
                        />
                    </div>
                )}
            </div>
        )
    }

    // ─── DOCUMENT ───
    if (messageType === 'document' && signedUrl) {
        const filename = mediaMetadata?.filename || 'Documento'
        const mime = mediaMetadata?.mime_type?.split(';')[0].trim() || ''
        const isPdf = mime === 'application/pdf'
        const fileSize = mediaMetadata?.file_size
        const sizeStr = fileSize ? (fileSize > 1024 * 1024 ? `${(fileSize / (1024 * 1024)).toFixed(1)} MB` : `${Math.round(fileSize / 1024)} KB`) : ''

        return (
            <a
                href={signedUrl}
                target="_blank"
                rel="noopener noreferrer"
                className="flex items-center gap-3 py-2.5 px-3.5 rounded-lg bg-slate-50 border border-slate-200 hover:bg-slate-100 transition-colors group"
            >
                <div className={`w-10 h-10 rounded-lg flex items-center justify-center flex-shrink-0 ${isPdf ? 'bg-red-100 text-red-600' : 'bg-blue-100 text-blue-600'}`}>
                    <FileText className="w-5 h-5" />
                </div>
                <div className="min-w-0 flex-1">
                    <div className="text-xs font-medium text-slate-700 truncate">{filename}</div>
                    <div className="text-[10px] text-slate-400">{mime.split('/').pop()?.toUpperCase()}{sizeStr ? ` · ${sizeStr}` : ''}</div>
                </div>
                <Download className="w-4 h-4 text-slate-400 group-hover:text-slate-600 transition-colors flex-shrink-0" />
            </a>
        )
    }

    // ─── AUDIO ───
    if (messageType === 'audio' && signedUrl) {
        return (
            <div className="w-full mb-1.5">
                <audio controls preload="none" className="w-full max-w-[280px] h-10" style={{ borderRadius: '8px' }}>
                    <source src={signedUrl} type={mediaMetadata?.mime_type?.split(';')[0].trim()} />
                    Tu navegador no soporta audio.
                </audio>
            </div>
        )
    }

    // ─── VIDEO ───
    if (messageType === 'video' && signedUrl) {
        return (
            <div className="mb-1.5">
                <video
                    controls
                    preload="none"
                    className="max-w-full max-h-[300px] rounded-lg"
                    style={{ backgroundColor: '#000' }}
                >
                    <source src={signedUrl} type={mediaMetadata?.mime_type?.split(';')[0].trim()} />
                    Tu navegador no soporta video.
                </video>
            </div>
        )
    }

    // ─── Fallback ───
    return null
}
