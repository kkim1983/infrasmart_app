/**
 * /api/v1/ocr/extract-pdf POST handler
 *
 * Next.js 리라이트 프록시는 기본 10MB body 제한이 있어
 * 대용량 PDF(17MB+) 업로드 시 실패합니다.
 * 이 Route Handler는 리라이트를 대체하여 스트리밍으로
 * 백엔드에 직접 전달하므로 크기 제한이 없습니다.
 * 응답은 Excel(blob) 이므로 arrayBuffer로 반환합니다.
 */

import { NextRequest, NextResponse } from 'next/server';

export const runtime = 'nodejs';

const BACKEND = process.env.BACKEND_INTERNAL_URL || 'http://localhost:8000';

export async function POST(req: NextRequest): Promise<NextResponse> {
  try {
    const contentType = req.headers.get('content-type') ?? '';
    const authorization = req.headers.get('authorization') ?? '';

    // req.arrayBuffer() reads the full body — no 10MB rewrite proxy limit here
    const body = await req.arrayBuffer();

    const response = await fetch(`${BACKEND}/api/v1/ocr/extract-pdf`, {
      method: 'POST',
      headers: {
        'content-type': contentType,
        ...(authorization ? { authorization } : {}),
      },
      body,
    });

    if (!response.ok) {
      const text = await response.text();
      return new NextResponse(text, {
        status: response.status,
        headers: { 'content-type': 'application/json' },
      });
    }

    // 성공: Excel 바이너리 응답을 그대로 전달
    const excelBuffer = await response.arrayBuffer();
    const contentDisposition = response.headers.get('content-disposition') ?? '';
    return new NextResponse(excelBuffer, {
      status: 200,
      headers: {
        'content-type':
          'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
        ...(contentDisposition ? { 'content-disposition': contentDisposition } : {}),
      },
    });
  } catch (err) {
    console.error('[/api/v1/ocr/extract-pdf] proxy error:', err);
    return NextResponse.json(
      { detail: 'PDF 손상물량표 추출 중 오류가 발생했습니다.' },
      { status: 502 }
    );
  }
}
