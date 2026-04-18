"use client";

import { useDeferredValue, useEffect, useState } from "react";
import Link from "next/link";

import { AuthGate } from "@/components/auth-gate";
import { Panel } from "@/components/panel";
import { apiFetch } from "@/lib/api";

type EntityItem = {
  id: string;
  display_name: string;
  canonical_name: string;
  entity_type: string;
  description?: string | null;
  aliases?: string[];
  confidence_score?: number | null;
};

const COMMON_CHINESE_SURNAMES =
  "赵钱孙李周吴郑王冯陈褚卫蒋沈韩杨朱秦尤许何吕施张孔曹严华金魏陶姜戚谢邹喻柏水窦章云苏潘葛奚范彭郎鲁韦昌马苗凤花方俞任袁柳鲍史唐费廉岑薛雷贺倪汤滕殷罗毕郝邬安常乐于时傅皮卞齐康伍余元卜顾孟平黄和穆萧尹姚邵湛汪祁毛禹狄米贝明臧计伏成戴谈宋茅庞熊纪舒屈项祝董梁杜阮蓝闵席季麻强贾路娄危江童颜郭梅盛林刁钟徐邱骆高夏蔡田樊胡凌霍虞万支柯昝管卢莫经房裘缪干解应宗丁宣贲邓郁单杭洪包诸左石崔吉钮龚程嵇邢滑裴陆荣翁荀羊於惠甄曲家封芮羿储靳汲邴糜松井段富巫乌焦巴弓牧隗山谷车侯宓蓬全郗班仰秋仲伊宫宁仇栾暴甘斜厉戎祖武符刘景詹束龙叶幸司韶郜黎蓟薄印宿白怀蒲台从鄂索咸籍赖卓蔺屠蒙池乔阴鬱胥能苍双闻莘党翟谭贡劳逄姬申扶堵冉宰郦雍郤璩桑桂濮牛寿通边扈燕冀郏浦尚农温别庄晏柴瞿阎充慕连茹习宦艾鱼容向古易慎戈廖庾终暨居衡步都耿满弘匡国文寇广禄阙东欧殳沃利蔚越夔隆师巩厍聂晁勾敖融冷訾辛阚那简饶空曾毋沙乜养鞠须丰巢关蒯相查后荆红游竺权逯盖益桓公";
const COMMON_COMPOUND_SURNAMES = ["欧阳", "司马", "上官", "诸葛", "东方", "独孤", "夏侯", "尉迟", "长孙", "宇文", "司徒", "司空", "慕容", "令狐"];
const INVALID_PERSON_SUFFIXES = ["在", "于", "的", "再"];

function looksLikePersonName(value: string): boolean {
  const candidate = value.trim();
  if (/^[A-Z][a-z]+(?:\s[A-Z][a-z]+){0,2}$/.test(candidate)) {
    return true;
  }
  if (!/^[\u4e00-\u9fff]{2,4}$/.test(candidate)) {
    return false;
  }
  if (/[和与及在于的]/.test(candidate)) {
    return false;
  }
  if (INVALID_PERSON_SUFFIXES.some((suffix) => candidate.endsWith(suffix))) {
    return false;
  }
  if (COMMON_COMPOUND_SURNAMES.some((surname) => candidate.startsWith(surname))) {
    return true;
  }
  return COMMON_CHINESE_SURNAMES.includes(candidate[0]);
}

export default function PeoplePage() {
  const [entities, setEntities] = useState<EntityItem[]>([]);
  const [query, setQuery] = useState("");
  const [error, setError] = useState("");
  const deferredQuery = useDeferredValue(query);

  useEffect(() => {
    apiFetch<{ items: EntityItem[] }>("/entities")
      .then((data) => {
        setEntities(data.items);
        setError("");
      })
      .catch((err) => {
        setEntities([]);
        setError(err instanceof Error ? err.message : "人物索引加载失败");
      });
  }, []);

  const peopleEntities = entities.filter((entity) => entity.entity_type === "person" && looksLikePersonName(entity.display_name));
  const normalizedQuery = deferredQuery.trim().toLowerCase();
  const filteredEntities = peopleEntities.filter((entity) => {
    if (!normalizedQuery) return true;
    return [
      entity.display_name,
      entity.canonical_name,
      entity.entity_type,
      ...(entity.aliases ?? []),
    ]
      .filter(Boolean)
      .some((value) => value.toLowerCase().includes(normalizedQuery));
  });

  return (
    <AuthGate>
      <main className="space-y-6">
        <section className="grid gap-6 xl:grid-cols-[1.2fr_0.8fr]">
          <Panel className="p-6 md:p-8" tone="default">
            <p className="text-sm font-black uppercase tracking-[0.2em]">People Index</p>
            <h1 className="mt-3 font-display text-[clamp(2.5rem,6vw,5rem)] leading-[0.9]">人物索引</h1>
            <p className="mt-4 max-w-3xl text-lg font-bold leading-relaxed">
              把输入文本中的人物、组织与关键称号汇成名册。这里优先展示可追踪、可跳转、可继续编排的角色节点。
            </p>
          </Panel>

          <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-1">
            <Panel className="p-5" tone="info">
              <p className="text-xs font-black uppercase tracking-[0.16em]">已识别角色</p>
              <p className="mt-3 text-5xl font-black">{peopleEntities.length}</p>
            </Panel>
            <Panel className="p-5" tone="signal">
              <p className="text-xs font-black uppercase tracking-[0.16em]">当前筛选结果</p>
              <p className="mt-3 text-5xl font-black">{filteredEntities.length}</p>
            </Panel>
          </div>
        </section>

        <Panel className="p-5" tone="default">
          <label className="text-xs font-black uppercase tracking-[0.16em]" htmlFor="people-query">
            快速检索
          </label>
          <input
            id="people-query"
            value={query}
            onChange={(event) => setQuery(event.target.value)}
            className="brutal-input mt-3 w-full text-lg font-semibold"
            placeholder="按名字、别名、类型搜索人物"
          />
        </Panel>

        {error ? (
          <Panel className="p-5 text-lg font-bold text-red-950" tone="danger">
            {error}
          </Panel>
        ) : null}

        {filteredEntities.length ? (
          <div className="grid gap-4 md:grid-cols-2 2xl:grid-cols-3">
            {filteredEntities.map((entity) => (
              <Link key={entity.id} href={`/story/entity/${entity.id}`}>
                <Panel
                  className="flex h-full flex-col justify-between p-5 transition-transform hover:-translate-y-1"
                  tone="default"
                >
                  <div>
                    <div className="flex items-start justify-between gap-4">
                      <p className="text-xs font-black uppercase tracking-[0.16em]">{entity.entity_type}</p>
                      {entity.confidence_score ? (
                        <p className="text-xs font-black uppercase tracking-[0.16em]">
                          {Math.round(entity.confidence_score * 100)}%
                        </p>
                      ) : null}
                    </div>
                    <p className="mt-4 text-3xl font-black">{entity.display_name}</p>
                    <p className="mt-2 text-base font-semibold opacity-80">{entity.canonical_name}</p>
                    <p className="mt-4 min-h-12 text-sm font-bold leading-relaxed">
                      {entity.description || "暂无角色注释，等待后续卷宗补足设定。"}
                    </p>
                  </div>

                  <div className="mt-5 flex flex-wrap gap-2">
                    {(entity.aliases ?? []).slice(0, 3).map((alias) => (
                      <span key={alias} className="brutal-chip">
                        {alias}
                      </span>
                    ))}
                    <span className="brutal-chip">
                      查看档案
                    </span>
                  </div>
                </Panel>
              </Link>
            ))}
          </div>
        ) : (
          <Panel className="p-6 text-lg font-bold" tone="default">
            当前没有可展示的人物索引。先去导入一条文本卷宗，或者换一个检索词试试。
          </Panel>
        )}
      </main>
    </AuthGate>
  );
}
