<template>
  <div class="settings-page">
    <div class="settings-header">
      <div>
        <h2>系统设置</h2>
        <p>集中维护云存储、微信服务号和云打印参数。</p>
      </div>
    </div>

    <a-card class="settings-tabs-card" :bordered="false">
      <a-tabs class="settings-tabs" v-model:activeKey="activeSettingsTab" @change="onSettingsTabChange">
        <a-tab-pane key="storage" tab="云存储配置">
          <div class="tab-panel-head">
            <span class="card-title">
              <CloudServerOutlined />
              云存储配置
            </span>
            <a-tag color="blue">{{ activeProviderLabel }}</a-tag>
          </div>

          <a-tabs v-model:activeKey="activeProvider" @change="onProviderChange">
            <a-tab-pane key="aliyun" tab="阿里云 OSS">
              <a-form layout="vertical" class="settings-form">
                <a-row :gutter="16">
                  <a-col :xs="24" :md="12">
                    <a-form-item label="启用状态">
                      <a-switch v-model:checked="storageConfig.enabled" checked-children="启用" un-checked-children="停用" />
                    </a-form-item>
                  </a-col>
                  <a-col :xs="24" :md="12">
                    <a-form-item label="Region">
                      <a-input v-model:value="storageConfig.region" placeholder="例如：oss-cn-hangzhou" />
                    </a-form-item>
                  </a-col>
                  <a-col :xs="24" :md="12">
                    <a-form-item label="AccessKey ID">
                      <a-input v-model:value="storageConfig.access_key_id" placeholder="请输入 AccessKey ID" />
                    </a-form-item>
                  </a-col>
                  <a-col :xs="24" :md="12">
                    <a-form-item label="AccessKey Secret">
                      <a-input-password v-model:value="storageConfig.access_key_secret" placeholder="请输入 AccessKey Secret" />
                    </a-form-item>
                  </a-col>
                  <a-col :xs="24" :md="12">
                    <a-form-item label="Bucket">
                      <a-input v-model:value="storageConfig.bucket" placeholder="请输入 Bucket 名称" />
                    </a-form-item>
                  </a-col>
                  <a-col :xs="24" :md="12">
                    <a-form-item label="Endpoint">
                      <a-input v-model:value="storageConfig.endpoint" placeholder="例如：oss-cn-hangzhou.aliyuncs.com" />
                    </a-form-item>
                  </a-col>
                </a-row>
              </a-form>
            </a-tab-pane>

            <a-tab-pane key="tencent" tab="腾讯云 COS">
              <a-form layout="vertical" class="settings-form">
                <a-row :gutter="16">
                  <a-col :xs="24" :md="12">
                    <a-form-item label="启用状态">
                      <a-switch v-model:checked="storageConfig.enabled" checked-children="启用" un-checked-children="停用" />
                    </a-form-item>
                  </a-col>
                  <a-col :xs="24" :md="12">
                    <a-form-item label="Region">
                      <a-input v-model:value="storageConfig.region" placeholder="例如：ap-guangzhou" />
                    </a-form-item>
                  </a-col>
                  <a-col :xs="24" :md="12">
                    <a-form-item label="SecretId">
                      <a-input v-model:value="storageConfig.secret_id" placeholder="请输入 SecretId" />
                    </a-form-item>
                  </a-col>
                  <a-col :xs="24" :md="12">
                    <a-form-item label="SecretKey">
                      <a-input-password v-model:value="storageConfig.secret_key" placeholder="请输入 SecretKey" />
                    </a-form-item>
                  </a-col>
                  <a-col :xs="24" :md="12">
                    <a-form-item label="Bucket">
                      <a-input v-model:value="storageConfig.bucket" placeholder="请输入 Bucket 名称" />
                    </a-form-item>
                  </a-col>
                </a-row>
              </a-form>
            </a-tab-pane>

            <a-tab-pane key="qiniu" tab="七牛云">
              <a-form layout="vertical" class="settings-form">
                <a-row :gutter="16">
                  <a-col :xs="24" :md="12">
                    <a-form-item label="启用状态">
                      <a-switch v-model:checked="storageConfig.enabled" checked-children="启用" un-checked-children="停用" />
                    </a-form-item>
                  </a-col>
                  <a-col :xs="24" :md="12">
                    <a-form-item label="Bucket">
                      <a-input v-model:value="storageConfig.bucket" placeholder="请输入 Bucket 名称" />
                    </a-form-item>
                  </a-col>
                  <a-col :xs="24" :md="12">
                    <a-form-item label="AccessKey">
                      <a-input v-model:value="storageConfig.access_key" placeholder="请输入 AccessKey" />
                    </a-form-item>
                  </a-col>
                  <a-col :xs="24" :md="12">
                    <a-form-item label="SecretKey">
                      <a-input-password v-model:value="storageConfig.secret_key" placeholder="请输入 SecretKey" />
                    </a-form-item>
                  </a-col>
                  <a-col :xs="24" :md="12">
                    <a-form-item label="访问域名">
                      <a-input v-model:value="storageConfig.domain" placeholder="例如：https://cdn.example.com" />
                    </a-form-item>
                  </a-col>
                </a-row>
              </a-form>
            </a-tab-pane>
          </a-tabs>

          <div class="card-actions">
            <a-space>
              <a-button type="primary" @click="saveStorageConfig" :loading="savingStorage">
                <template #icon><SaveOutlined /></template>
                保存云存储配置
              </a-button>
              <a-button @click="testConnection" :loading="testingStorage">
                <template #icon><ExperimentOutlined /></template>
                测试连接
              </a-button>
            </a-space>
          </div>
        </a-tab-pane>

        <a-tab-pane key="wechat" tab="微信服务号配置">
          <div class="tab-panel-head">
            <span class="card-title">
              <WechatOutlined />
              微信服务号配置
            </span>
            <a-tag :color="wechatConfig.enabled ? 'green' : 'default'">
              {{ wechatConfig.enabled ? '已启用' : '未启用' }}
            </a-tag>
          </div>

          <a-alert
            class="info-alert"
            type="info"
            show-icon
            message="用于微信浏览器内获取观众 openid、头像和昵称"
            description="请在微信公众平台网页授权域名中配置当前访问域名；授权回调页使用 /p/index、/p/{活动ID} 和 /p/{节目token}。"
          />

          <a-form layout="vertical" class="settings-form">
            <a-row :gutter="16">
              <a-col :xs="24" :md="8">
                <a-form-item label="启用微信授权">
                  <a-switch v-model:checked="wechatConfig.enabled" checked-children="启用" un-checked-children="停用" />
                </a-form-item>
              </a-col>
              <a-col :xs="24" :md="8">
                <a-form-item label="AppID">
                  <a-input v-model:value="wechatConfig.appid" placeholder="请输入微信服务号 AppID" />
                </a-form-item>
              </a-col>
              <a-col :xs="24" :md="8">
                <a-form-item label="网页授权 Scope">
                  <a-select v-model:value="wechatConfig.scope" :options="wechatScopeOptions" />
                </a-form-item>
              </a-col>
              <a-col :xs="24" :md="16">
                <a-form-item label="AppSecret">
                  <a-input-password v-model:value="wechatConfig.appsecret" placeholder="请输入微信服务号 AppSecret" />
                </a-form-item>
              </a-col>
              <a-col :xs="24" :md="8">
                <a-form-item label="State">
                  <a-input v-model:value="wechatConfig.state" placeholder="supertech" />
                </a-form-item>
              </a-col>
            </a-row>
          </a-form>

          <div class="card-actions">
            <a-button type="primary" @click="saveWechatConfig" :loading="savingWechat">
              <template #icon><SaveOutlined /></template>
              保存微信配置
            </a-button>
          </div>
        </a-tab-pane>

        <a-tab-pane key="network" tab="网络设置">
          <div class="tab-panel-head">
            <span class="card-title">
              <LinkOutlined />
              网络设置
            </span>
            <a-tag :color="networkConfig.ssl_enabled ? 'green' : 'blue'">
              {{ networkConfig.base_url || '未设置域名' }}
            </a-tag>
          </div>

          <a-alert
            class="info-alert"
            type="info"
            show-icon
            message="统一维护公网域名、baseUrl 和 SSL 证书"
            description="设置域名后，微信支付回调、退款回调和其他需要填写公网 URL 的位置都可以复用这里生成的地址。启用 SSL 后会生成 Nginx HTTPS 配置，需重启 web 容器生效。"
          />

          <a-form layout="vertical" class="settings-form">
            <a-row :gutter="16">
              <a-col :xs="24" :md="8">
                <a-form-item label="公网域名">
                  <a-input v-model:value="networkConfig.domain" placeholder="wechat.vidiu.cn" />
                </a-form-item>
              </a-col>
              <a-col :xs="24" :md="8">
                <a-form-item label="Base URL">
                  <a-input v-model:value="networkConfig.base_url" placeholder="https://wechat.vidiu.cn" />
                </a-form-item>
              </a-col>
              <a-col :xs="24" :md="4">
                <a-form-item label="启用 SSL">
                  <a-switch v-model:checked="networkConfig.ssl_enabled" checked-children="开启" un-checked-children="关闭" />
                </a-form-item>
              </a-col>
              <a-col :xs="24" :md="4">
                <a-form-item label="HTTPS 优先">
                  <a-switch v-model:checked="networkConfig.force_https" checked-children="开启" un-checked-children="关闭" />
                </a-form-item>
              </a-col>
            </a-row>

            <a-row :gutter="16">
              <a-col :xs="24" :md="12">
                <a-form-item label="SSL 证书 PEM">
                  <input type="file" accept=".pem,.crt,.cer" @change="event => readPemFile(event, 'cert')" />
                  <a-textarea v-model:value="networkConfig.ssl_cert_pem" :rows="6" placeholder="-----BEGIN CERTIFICATE-----" />
                </a-form-item>
              </a-col>
              <a-col :xs="24" :md="12">
                <a-form-item label="SSL 私钥 KEY / PEM">
                  <input type="file" accept=".pem,.key" @change="event => readPemFile(event, 'key')" />
                  <a-textarea v-model:value="networkConfig.ssl_key_pem" :rows="6" placeholder="-----BEGIN PRIVATE KEY-----" />
                </a-form-item>
              </a-col>
            </a-row>
          </a-form>

          <a-descriptions bordered size="small" :column="1" class="network-preview">
            <a-descriptions-item label="支付回调">
              {{ networkConfig.wechat_pay_notify_url || derivedNotifyUrl }}
            </a-descriptions-item>
            <a-descriptions-item label="退款回调">
              {{ networkConfig.wechat_pay_refund_notify_url || derivedRefundNotifyUrl }}
            </a-descriptions-item>
            <a-descriptions-item label="证书状态">
              证书 {{ networkConfig.has_ssl_cert ? '已上传' : '未上传' }}，
              私钥 {{ networkConfig.has_ssl_key ? '已上传' : '未上传' }}
            </a-descriptions-item>
          </a-descriptions>

          <div class="card-actions">
            <a-space>
              <a-button type="primary" @click="saveNetworkConfig" :loading="savingNetwork">
                <template #icon><SaveOutlined /></template>
                保存网络设置
              </a-button>
              <a-button @click="applyNetworkUrls">
                <template #icon><LinkOutlined /></template>
                填入微信支付回调
              </a-button>
            </a-space>
          </div>
        </a-tab-pane>

        <a-tab-pane key="wechat-pay" tab="微信支付配置">
          <div class="tab-panel-head">
            <span class="card-title">
              <WechatOutlined />
              微信支付配置
            </span>
            <a-tag :color="wechatPayConfig.enabled ? 'green' : 'default'">
              {{ wechatPayConfig.enabled ? '已启用' : '未启用' }}
            </a-tag>
          </div>

          <a-alert
            class="info-alert"
            type="info"
            show-icon
            message="用于照片打印超出免费额度后的微信支付"
            description="密钥和私钥只在输入新值时更新；留空会保留服务端已保存的值。"
          />

          <a-form layout="vertical" class="settings-form">
            <section class="form-section">
              <div class="section-title">基础参数</div>
              <a-row :gutter="16">
                <a-col :xs="24" :md="8">
                  <a-form-item label="启用微信支付">
                    <a-switch v-model:checked="wechatPayConfig.enabled" checked-children="启用" un-checked-children="停用" />
                  </a-form-item>
                </a-col>
                <a-col :xs="24" :md="8">
                  <a-form-item label="AppID">
                    <a-input v-model:value="wechatPayConfig.appid" placeholder="微信支付关联公众号或小程序 AppID" />
                  </a-form-item>
                </a-col>
                <a-col :xs="24" :md="8">
                  <a-form-item label="商户号 MCHID">
                    <a-input v-model:value="wechatPayConfig.mchid" placeholder="微信支付商户号" />
                  </a-form-item>
                </a-col>
                <a-col :xs="24" :md="8">
                  <a-form-item label="商户证书序列号">
                    <a-input v-model:value="wechatPayConfig.merchant_serial_no" placeholder="merchant serial no" />
                  </a-form-item>
                </a-col>
                <a-col :xs="24" :md="16">
                  <a-form-item label="订单描述">
                    <a-input v-model:value="wechatPayConfig.description" placeholder="例如：照片打印" />
                  </a-form-item>
                </a-col>
              </a-row>
            </section>

            <section class="form-section">
              <div class="section-title">密钥与证书</div>
              <a-row :gutter="16">
                <a-col :xs="24" :md="12">
                  <a-form-item label="API v3 密钥">
                    <a-input-password
                      v-model:value="wechatPayConfig.api_v3_key"
                      :placeholder="wechatPayConfig.has_api_v3_key ? '已配置，输入新值可覆盖' : '请输入 API v3 密钥'"
                    />
                  </a-form-item>
                </a-col>
                <a-col :xs="24" :md="12">
                  <a-form-item label="API v2 密钥（兼容旧接口）">
                    <a-input-password
                      v-model:value="wechatPayConfig.api_key"
                      :placeholder="wechatPayConfig.has_api_key ? '已配置，输入新值可覆盖' : '请输入 API v2 密钥'"
                    />
                  </a-form-item>
                </a-col>
                <a-col :xs="24" :md="24">
                  <a-form-item label="商户私钥 private_key">
                    <a-textarea
                      v-model:value="wechatPayConfig.private_key"
                      :rows="6"
                      :placeholder="wechatPayConfig.has_private_key ? '已配置，粘贴新私钥可覆盖' : '粘贴 apiclient_key.pem 内容'"
                    />
                  </a-form-item>
                </a-col>
              </a-row>
            </section>

            <section class="form-section">
              <div class="section-title">回调地址</div>
              <a-row :gutter="16">
                <a-col :xs="24" :md="12">
                  <a-form-item label="支付回调 URL">
                    <a-input v-model:value="wechatPayConfig.notify_url" placeholder="https://example.com/api/public/print/wechat-notify" />
                  </a-form-item>
                </a-col>
                <a-col :xs="24" :md="12">
                  <a-form-item label="退款回调 URL">
                    <a-input v-model:value="wechatPayConfig.refund_notify_url" placeholder="可选，退款通知地址" />
                  </a-form-item>
                </a-col>
              </a-row>
            </section>
          </a-form>

          <div class="card-actions">
            <a-button type="primary" @click="saveWechatPayConfig" :loading="savingWechatPay">
              <template #icon><SaveOutlined /></template>
              保存微信支付配置
            </a-button>
          </div>
        </a-tab-pane>

        <a-tab-pane v-if="false" key="print" tab="云打印配置">
          <div class="tab-panel-head">
            <span class="card-title">
              <PrinterOutlined />
              云打印配置
            </span>
            <a-tag color="green">蓝阔</a-tag>
          </div>

          <a-alert
            class="info-alert"
            type="info"
            show-icon
            message="按蓝阔云打印文档设计"
            description="API 域名使用 cloud.liankenet.com；每个请求需要在 Header 中携带 ApiKey；设备凭证来自云盒二维码中的 deviceId 与 deviceKey。"
          />

          <div class="print-config-layout">
            <div class="print-form-column">
          <a-form layout="vertical" class="settings-form">
            <section class="form-section">
              <div class="section-title">服务凭证</div>
              <a-row :gutter="16">
                <a-col :xs="24" :md="8">
                  <a-form-item label="启用云打印">
                    <a-switch v-model:checked="printConfig.enabled" checked-children="启用" un-checked-children="停用" />
                  </a-form-item>
                </a-col>
                <a-col :xs="24" :md="8">
                  <a-form-item label="服务商">
                    <a-input v-model:value="printConfig.providerName" disabled />
                  </a-form-item>
                </a-col>
                <a-col :xs="24" :md="8">
                  <a-form-item label="API 服务器">
                    <a-input v-model:value="printConfig.apiBaseUrl" placeholder="https://cloud.liankenet.com" />
                  </a-form-item>
                </a-col>
                <a-col :xs="24" :md="24">
                  <a-form-item label="ApiKey">
                    <a-input-password v-model:value="printConfig.ApiKey" placeholder="开放平台申请的开发者 ApiKey" />
                  </a-form-item>
                </a-col>
              </a-row>
            </section>

            <section class="form-section">
              <div class="section-title">设备与打印机</div>
              <a-row :gutter="16">
                <a-col :xs="24" :md="8">
                  <a-form-item label="deviceId（云账号）">
                    <a-input v-model:value="printConfig.deviceId" placeholder="从云盒二维码解析获得" />
                  </a-form-item>
                </a-col>
                <a-col :xs="24" :md="8">
                  <a-form-item label="deviceKey（云密码）">
                    <a-input-password v-model:value="printConfig.deviceKey" placeholder="从云盒二维码解析获得" />
                  </a-form-item>
                </a-col>
                <a-col :xs="24" :md="8">
                  <a-form-item label="devicePort">
                    <a-select v-model:value="printConfig.devicePort" :options="devicePortOptions" />
                  </a-form-item>
                </a-col>
                <a-col :xs="24" :md="8">
                  <a-form-item label="printerType">
                    <a-select v-model:value="printConfig.printerType" :options="printerTypeOptions" />
                  </a-form-item>
                </a-col>
                <a-col :xs="24" :md="8">
                  <a-form-item label="printerModel">
                    <a-input v-model:value="printConfig.printerModel" placeholder="对应 printer_list 返回的 driver_name" />
                  </a-form-item>
                </a-col>
                <a-col :xs="24" :md="8">
                  <a-form-item label="targetIp（网络打印机）">
                    <a-input v-model:value="printConfig.targetIp" placeholder="局域网打印机 IP，可选" />
                  </a-form-item>
                </a-col>
              </a-row>
            </section>

            <section class="form-section">
              <div class="section-title">默认打印参数</div>
              <a-row :gutter="16">
                <a-col :xs="24" :md="8">
                  <a-form-item label="纸张尺寸 dmPaperSize">
                    <a-select v-model:value="printConfig.dmPaperSize" :options="paperSizeOptions" />
                  </a-form-item>
                </a-col>
                <a-col :xs="24" :md="8">
                  <a-form-item label="打印方向 dmOrientation">
                    <a-select v-model:value="printConfig.dmOrientation" :options="orientationOptions" />
                  </a-form-item>
                </a-col>
                <a-col :xs="24" :md="8">
                  <a-form-item label="打印份数 dmCopies">
                    <a-input-number v-model:value="printConfig.dmCopies" :min="1" :max="999" style="width: 100%" />
                  </a-form-item>
                </a-col>
                <a-col :xs="24" :md="8">
                  <a-form-item label="打印颜色 dmColor">
                    <a-select v-model:value="printConfig.dmColor" :options="colorOptions" />
                  </a-form-item>
                </a-col>
                <a-col :xs="24" :md="8">
                  <a-form-item label="双面打印 dmDuplex">
                    <a-select v-model:value="printConfig.dmDuplex" :options="duplexOptions" />
                  </a-form-item>
                </a-col>
                <a-col :xs="24" :md="8">
                  <a-form-item label="缩放 jpScale">
                    <a-select v-model:value="printConfig.jpScale" :options="scaleOptions" />
                  </a-form-item>
                </a-col>
                <a-col v-if="printConfig.dmPaperSize === '0'" :xs="24" :md="8">
                  <a-form-item label="自定义纸宽 dmPaperWidth（0.1mm）">
                    <a-input-number v-model:value="printConfig.dmPaperWidth" :min="1" style="width: 100%" />
                  </a-form-item>
                </a-col>
                <a-col v-if="printConfig.dmPaperSize === '0'" :xs="24" :md="8">
                  <a-form-item label="自定义纸高 dmPaperLength（0.1mm）">
                    <a-input-number v-model:value="printConfig.dmPaperLength" :min="1" style="width: 100%" />
                  </a-form-item>
                </a-col>
              </a-row>
            </section>

            <section class="form-section">
              <div class="section-title">高级选项</div>
              <a-row :gutter="16">
                <a-col :xs="24" :md="8">
                  <a-form-item label="HTML 转换内核 htmlKernel">
                    <a-select v-model:value="printConfig.htmlKernel" :options="htmlKernelOptions" />
                  </a-form-item>
                </a-col>
                <a-col :xs="24" :md="8">
                  <a-form-item label="自动对齐 jpAutoAlign">
                    <a-select v-model:value="printConfig.jpAutoAlign" :options="alignOptions" />
                  </a-form-item>
                </a-col>
                <a-col :xs="24" :md="8">
                  <a-form-item label="页码范围 jpPageRange">
                    <a-input v-model:value="printConfig.jpPageRange" placeholder="例如：1,2,5-10；留空为全部" />
                  </a-form-item>
                </a-col>
                <a-col :xs="24" :md="8">
                  <a-form-item label="打印质量 dmPrintQuality">
                    <a-select v-model:value="printConfig.dmPrintQuality" :options="qualityOptions" allow-clear />
                  </a-form-item>
                </a-col>
                <a-col v-if="hasMediaTypeOptions" :xs="24" :md="8">
                  <a-form-item label="介质类型 dmMediaType">
                    <a-select
                      v-model:value="printConfig.dmMediaType"
                      :options="effectiveMediaTypeOptions"
                      allow-clear
                    />
                  </a-form-item>
                </a-col>
                <a-col :xs="24" :md="8">
                  <a-form-item label="连续错误上限 errLimitNum">
                    <a-input-number v-model:value="printConfig.errLimitNum" :min="1" :max="30" style="width: 100%" />
                  </a-form-item>
                </a-col>
                <a-col :xs="24" :md="24">
                  <a-form-item label="打印结果回调 callbackUrl">
                    <a-input v-model:value="printConfig.callbackUrl" placeholder="必须为 https 链接，留空则轮询任务状态" />
                  </a-form-item>
                </a-col>
                <a-col :xs="24" :md="8">
                  <a-form-item label="拦截设备异常">
                    <a-switch v-model:checked="printConfig.reportDeviceStatus" checked-children="开启" un-checked-children="关闭" />
                  </a-form-item>
                </a-col>
                <a-col :xs="24" :md="8">
                  <a-form-item label="拦截打印机异常">
                    <a-switch v-model:checked="printConfig.reportPrinterStatus" checked-children="开启" un-checked-children="关闭" />
                  </a-form-item>
                </a-col>
                <a-col :xs="24" :md="8">
                  <a-form-item label="文档逆序">
                    <a-switch v-model:checked="printConfig.pdfRev" checked-children="开启" un-checked-children="关闭" />
                  </a-form-item>
                </a-col>
                <a-col :xs="24" :md="8">
                  <a-form-item label="自动旋转">
                    <a-switch v-model:checked="printConfig.jpAutoRotate" checked-children="开启" un-checked-children="关闭" />
                  </a-form-item>
                </a-col>
              </a-row>
            </section>
          </a-form>

          <div class="card-actions">
            <a-space>
              <a-button type="primary" @click="savePrintConfig" :loading="savingPrint">
                <template #icon><SaveOutlined /></template>
                保存云打印配置
              </a-button>
              <a-button href="https://documenter.getpostman.com/view/1758872/SWE83H6u?version=latest" target="_blank">
                <template #icon><LinkOutlined /></template>
                查看开发文档
              </a-button>
            </a-space>
          </div>
            </div>

            <aside class="printer-inspector">
              <div class="printer-inspector-head">
                <div>
                  <span class="inspector-title">
                    <PrinterOutlined />
                    打印机状态
                  </span>
                  <div class="inspector-subtitle">
                    在线 {{ printerInfo.online_printers.length }} / 总计 {{ printerInfo.printers.length }}
                  </div>
                </div>
                <a-button size="small" :loading="loadingPrinterInfo" @click="loadPrinterInfo(true)">
                  <template #icon><ReloadOutlined /></template>
                </a-button>
              </div>

              <a-spin :spinning="loadingPrinterInfo">
                <a-alert
                  v-if="printerInfoError"
                  class="printer-alert"
                  type="warning"
                  show-icon
                  :message="printerInfoError"
                />
                <a-empty
                  v-else-if="!printerInfo.printers.length"
                  class="printer-empty"
                  description="暂无打印机信息"
                />
                <div v-else>
                  <div class="printer-list">
                    <button
                      v-for="printer in printerInfo.online_printers"
                      :key="printerKey(printer)"
                      type="button"
                      class="printer-row"
                      :class="{ active: printerKey(printer) === selectedPrinterKey }"
                      @click="selectPrinter(printer)"
                    >
                      <span>
                        <strong>{{ printer.printer_name || printer.driver_name }}</strong>
                        <small>{{ printer.driver_name }}</small>
                      </span>
                      <a-tag :color="printerStatusColor(printer)">{{ printer.status_label }}</a-tag>
                    </button>
                  </div>

                  <a-descriptions
                    v-if="printerInfo.selected_printer"
                    class="printer-desc"
                    size="small"
                    :column="1"
                    bordered
                  >
                    <a-descriptions-item label="printerModel">
                      {{ printerInfo.selected_model || '-' }}
                    </a-descriptions-item>
                    <a-descriptions-item label="devicePort">
                      {{ printerInfo.selected_printer?.port === 631 ? '1（网络打印机）' : printerInfo.selected_printer?.port || '-' }}
                    </a-descriptions-item>
                    <a-descriptions-item label="printer_state">
                      {{ printerInfo.selected_printer?.printer_state || printerInfo.selected_printer?.status_label || '-' }}
                    </a-descriptions-item>
                    <a-descriptions-item label="support_status">
                      {{ printerInfo.selected_printer?.support_status ? '支持' : '未声明' }}
                    </a-descriptions-item>
                  </a-descriptions>

                  <div v-if="printerInfo.printer_params && Object.keys(printerInfo.printer_params).length" class="printer-params">
                    <div class="params-head">
                      <span>打印机参数</span>
                      <a-tag v-if="printerInfo.params_cached" color="blue">缓存</a-tag>
                      <a-tag v-else color="green">已刷新</a-tag>
                    </div>
                    <div class="params-grid">
                      <div>
                        <span>纸张</span>
                        <strong>{{ optionCount(printerInfo.printer_params?.Capabilities?.Papers) }}</strong>
                      </div>
                      <div>
                        <span>介质</span>
                        <strong>{{ mediaTypeOptions.length }}</strong>
                      </div>
                      <div>
                        <span>DPI</span>
                        <strong>{{ printerDpi }}</strong>
                      </div>
                      <div>
                        <span>色彩</span>
                        <strong>{{ optionCount(printerInfo.printer_params?.Capabilities?.Color) }}</strong>
                      </div>
                    </div>
                    <div v-if="mediaTypeOptions.length" class="media-options">
                      <a-tag v-for="item in mediaTypeOptions.slice(0, 8)" :key="item.value">
                        {{ item.label }}
                      </a-tag>
                    </div>
                  </div>
                </div>
              </a-spin>
            </aside>
          </div>
        </a-tab-pane>

        <a-tab-pane key="print-client" tab="本地打印客户端">
          <div class="tab-panel-head">
            <span class="card-title">
              <PrinterOutlined />
              本地打印客户端
            </span>
            <a-tag color="green">supertech-PhotoPrinter</a-tag>
          </div>

          <a-alert
            class="info-alert"
            type="info"
            show-icon
            message="用于本地电脑领取打印订单"
            description="此密钥需要与 supertech-PhotoPrinter 客户端设置页中的客户端 Token 保持一致；客户端请求会通过 X-Print-Client-Token 传递。"
          />

          <a-form layout="vertical" class="settings-form">
            <a-row :gutter="16">
              <a-col :xs="24" :md="16">
                <a-form-item label="客户端共享密钥 print_client_token">
                  <a-input-password
                    v-model:value="printClientToken"
                    placeholder="请输入一段足够长的随机密钥"
                    allow-clear
                  />
                </a-form-item>
              </a-col>
              <a-col :xs="24" :md="8">
                <a-form-item label="派发模式">
                  <a-input value="由活动打印设置控制 print_dispatch_mode" disabled />
                </a-form-item>
              </a-col>
            </a-row>
          </a-form>

          <div class="card-actions">
            <a-button type="primary" @click="savePrintClientConfig" :loading="savingPrintClient">
              <template #icon><SaveOutlined /></template>
              保存本地客户端密钥
            </a-button>
          </div>
        </a-tab-pane>

        <a-tab-pane key="roles" tab="角色管理">
          <RoleManagement />
        </a-tab-pane>
      </a-tabs>
    </a-card>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, reactive, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import {
  CloudServerOutlined,
  ExperimentOutlined,
  LinkOutlined,
  PrinterOutlined,
  ReloadOutlined,
  SaveOutlined,
  WechatOutlined,
} from '@ant-design/icons-vue'
import { message } from 'ant-design-vue'
import request from '@/api/request'
import RoleManagement from './RoleManagement.vue'

type SettingValue = string | number | boolean | null
type StorageConfig = Record<string, SettingValue>

interface OptionItem {
  label: string
  value: string
}

interface LankuoPrintConfig {
  enabled: boolean
  provider: 'lankuo'
  providerName: string
  apiBaseUrl: string
  ApiKey: string
  deviceId: string
  deviceKey: string
  devicePort: string
  printerType: string
  printerModel: string
  targetIp: string
  dmPaperSize: string
  dmOrientation: string
  dmCopies: number
  dmColor: string
  dmDuplex: string
  dmDefaultSource: string
  dmMediaType: string
  dmPaperLength: number
  dmPaperWidth: number
  dmPrintQuality: string
  jpScale: string
  jpAutoAlign: string
  jpPageRange: string
  htmlKernel: string
  callbackUrl: string
  reportDeviceStatus: boolean
  reportPrinterStatus: boolean
  errLimitNum: number
  pdfRev: boolean
  jpAutoRotate: boolean
}

interface PrinterItem {
  [key: string]: any
  driver_name: string
  printer_name?: string
  printer_state?: string
  port?: number | string
  ip_addr?: string
  support_status?: boolean
  is_online?: boolean
  status_label?: string
  status_level?: string
}

interface LankuoPrinterInfo {
  configured: boolean
  printers: PrinterItem[]
  online_printers: PrinterItem[]
  selected_printer: PrinterItem | null
  selected_model: string
  printer_params: Record<string, any>
  params_cached: boolean
  params_cached_at?: string | null
  media_type_options: OptionItem[]
  paper_options: OptionItem[]
}

interface WechatOfficialConfig {
  enabled: boolean
  appid: string
  appsecret: string
  scope: 'snsapi_userinfo' | 'snsapi_base'
  state: string
}

interface WechatPayConfig {
  enabled: boolean
  appid: string
  mchid: string
  api_key: string
  api_v3_key: string
  merchant_serial_no: string
  private_key: string
  notify_url: string
  refund_notify_url: string
  description: string
  has_api_key: boolean
  has_api_v3_key: boolean
  has_private_key: boolean
}

interface NetworkConfig {
  domain: string
  base_url: string
  ssl_enabled: boolean
  force_https: boolean
  ssl_cert_pem?: string
  ssl_key_pem?: string
  has_ssl_cert: boolean
  has_ssl_key: boolean
  wechat_pay_notify_url: string
  wechat_pay_refund_notify_url: string
}

const activeProvider = ref('aliyun')
const route = useRoute()
const router = useRouter()
const savingStorage = ref(false)
const testingStorage = ref(false)
const savingPrint = ref(false)
const savingWechat = ref(false)
const savingWechatPay = ref(false)
const savingNetwork = ref(false)
const savingPrintClient = ref(false)
const printClientToken = ref('')

const storageProviderLabels: Record<string, string> = {
  aliyun: '阿里云 OSS',
  tencent: '腾讯云 COS',
  qiniu: '七牛云',
}

const defaultStorageConfigs: Record<string, StorageConfig> = {
  aliyun: {
    enabled: false,
    access_key_id: '',
    access_key_secret: '',
    bucket: '',
    endpoint: '',
    region: 'oss-cn-hangzhou',
  },
  tencent: {
    enabled: false,
    secret_id: '',
    secret_key: '',
    bucket: '',
    region: 'ap-guangzhou',
  },
  qiniu: {
    enabled: false,
    access_key: '',
    secret_key: '',
    bucket: '',
    domain: '',
  },
}

const defaultPrintConfig: LankuoPrintConfig = {
  enabled: false,
  provider: 'lankuo',
  providerName: '蓝阔（链科云打印 v3）',
  apiBaseUrl: 'https://cloud.liankenet.com',
  ApiKey: '',
  deviceId: '',
  deviceKey: '',
  devicePort: '1',
  printerType: '1',
  printerModel: '',
  targetIp: '',
  dmPaperSize: '9',
  dmOrientation: '1',
  dmCopies: 1,
  dmColor: '2',
  dmDuplex: '1',
  dmDefaultSource: '',
  dmMediaType: '',
  dmPaperLength: 300,
  dmPaperWidth: 200,
  dmPrintQuality: '',
  jpScale: 'fit',
  jpAutoAlign: 'z5',
  jpPageRange: '',
  htmlKernel: 'chrometopdf',
  callbackUrl: '',
  reportDeviceStatus: true,
  reportPrinterStatus: true,
  errLimitNum: 30,
  pdfRev: false,
  jpAutoRotate: false,
}

const defaultWechatConfig: WechatOfficialConfig = {
  enabled: false,
  appid: '',
  appsecret: '',
  scope: 'snsapi_userinfo',
  state: 'supertech',
}

const defaultWechatPayConfig: WechatPayConfig = {
  enabled: false,
  appid: '',
  mchid: '',
  api_key: '',
  api_v3_key: '',
  merchant_serial_no: '',
  private_key: '',
  notify_url: '',
  refund_notify_url: '',
  description: '照片打印',
  has_api_key: false,
  has_api_v3_key: false,
  has_private_key: false,
}

const defaultNetworkConfig: NetworkConfig = {
  domain: '',
  base_url: '',
  ssl_enabled: false,
  force_https: true,
  ssl_cert_pem: '',
  ssl_key_pem: '',
  has_ssl_cert: false,
  has_ssl_key: false,
  wechat_pay_notify_url: '',
  wechat_pay_refund_notify_url: '',
}

const storageConfig = reactive<StorageConfig>({ ...defaultStorageConfigs.aliyun })
const printConfig = reactive<LankuoPrintConfig>({ ...defaultPrintConfig })
const wechatConfig = reactive<WechatOfficialConfig>({ ...defaultWechatConfig })
const wechatPayConfig = reactive<WechatPayConfig>({ ...defaultWechatPayConfig })
const networkConfig = reactive<NetworkConfig>({ ...defaultNetworkConfig })
const printerInfo = reactive<LankuoPrinterInfo>({
  configured: false,
  printers: [],
  online_printers: [],
  selected_printer: null,
  selected_model: '',
  printer_params: {},
  params_cached: false,
  params_cached_at: null,
  media_type_options: [],
  paper_options: [],
})
const loadingPrinterInfo = ref(false)
const printerInfoError = ref('')
const selectedPrinterKey = ref('')
const mediaTypeOptions = ref<OptionItem[]>([])

const activeProviderLabel = computed(() => storageProviderLabels[activeProvider.value] || activeProvider.value)
const effectiveMediaTypeOptions = computed(() => {
  const options = [...mediaTypeOptions.value]
  const current = String(printConfig.dmMediaType || '')
  if (current && !options.some(item => item.value === current)) {
    options.unshift({ label: `当前值 ${current}`, value: current })
  }
  return options
})
const hasMediaTypeOptions = computed(() => effectiveMediaTypeOptions.value.length > 0)
const printerDpi = computed(() => {
  const ctx = printerInfo.printer_params?.DeviceContext || {}
  const devMode = printerInfo.printer_params?.DevMode || {}
  return ctx.LogPixelsX && ctx.LogPixelsY
    ? `${ctx.LogPixelsX}x${ctx.LogPixelsY}`
    : String(devMode.PrintQuality || '-')
})

const derivedBaseUrl = computed(() => {
  const text = (networkConfig.base_url || networkConfig.domain || '').trim().replace(/\/+$/, '')
  if (!text) return ''
  if (networkConfig.ssl_enabled && text.startsWith('http://')) return `https://${text.slice('http://'.length)}`
  if (text.startsWith('http://') || text.startsWith('https://')) return text
  return `${networkConfig.ssl_enabled ? 'https' : 'http'}://${text}`
})
const derivedNotifyUrl = computed(() => derivedBaseUrl.value ? `${derivedBaseUrl.value}/api/public/print/wechat-notify` : '')
const derivedRefundNotifyUrl = computed(() => derivedBaseUrl.value ? `${derivedBaseUrl.value}/api/public/print/wechat-refund-notify` : '')

const settingTabs = ['storage', 'wechat', 'network', 'wechat-pay', 'print-client', 'roles']
const activeSettingsTab = ref(
  typeof route.query.tab === 'string' && settingTabs.includes(route.query.tab)
    ? route.query.tab
    : 'storage',
)

const onSettingsTabChange = (key: string) => {
  router.replace({
    path: route.path,
    query: {
      ...route.query,
      tab: key === 'storage' ? undefined : key,
    },
  })
}

watch(
  () => route.query.tab,
  value => {
    if (typeof value === 'string' && settingTabs.includes(value)) {
      activeSettingsTab.value = value
    } else if (!value) {
      activeSettingsTab.value = 'storage'
    }
  },
)

const devicePortOptions: OptionItem[] = [
  { label: 'USB1 / 网络打印机默认', value: '1' },
  { label: 'USB2', value: '2' },
  { label: 'USB3', value: '3' },
  { label: 'USB4', value: '4' },
]

const printerTypeOptions: OptionItem[] = [
  { label: '打印机', value: '1' },
]

const paperSizeOptions: OptionItem[] = [
  { label: 'A4（9）', value: '9' },
  { label: 'A5（11）', value: '11' },
  { label: 'A6（70）', value: '70' },
  { label: 'Letter（1）', value: '1' },
  { label: 'Legal（5）', value: '5' },
  { label: '自定义尺寸（0）', value: '0' },
]

const orientationOptions: OptionItem[] = [
  { label: '纵向（1）', value: '1' },
  { label: '横向（2）', value: '2' },
]

const colorOptions: OptionItem[] = [
  { label: '黑白（1）', value: '1' },
  { label: '彩色（2）', value: '2' },
]

const duplexOptions: OptionItem[] = [
  { label: '关闭（1）', value: '1' },
  { label: '长边翻转（2）', value: '2' },
  { label: '短边翻转（3）', value: '3' },
]

const scaleOptions: OptionItem[] = [
  { label: 'fit 自适应', value: 'fit' },
  { label: 'fitw 宽度优先', value: 'fitw' },
  { label: 'fith 高度优先', value: 'fith' },
  { label: 'fill 拉伸全图', value: 'fill' },
  { label: 'cover 自动裁剪铺满', value: 'cover' },
  { label: 'none 不缩放', value: 'none' },
]

const alignOptions: OptionItem[] = [
  { label: '左上 z1', value: 'z1' },
  { label: '中上 z2', value: 'z2' },
  { label: '右上 z3', value: 'z3' },
  { label: '左中 z4', value: 'z4' },
  { label: '居中 z5', value: 'z5' },
  { label: '右中 z6', value: 'z6' },
  { label: '左下 z7', value: 'z7' },
  { label: '中下 z8', value: 'z8' },
  { label: '右下 z9', value: 'z9' },
]

const htmlKernelOptions: OptionItem[] = [
  { label: 'chrometopdf（推荐）', value: 'chrometopdf' },
  { label: 'wkhtmltopdf', value: 'wkhtmltopdf' },
  { label: 'wkhtml', value: 'wkhtml' },
]

const qualityOptions: OptionItem[] = [
  { label: '-1 最低质量', value: '-1' },
  { label: '-2 较低质量', value: '-2' },
  { label: '-3 较高质量', value: '-3' },
  { label: '-4 最高质量', value: '-4' },
]

const wechatScopeOptions: OptionItem[] = [
  { label: 'snsapi_userinfo（获取头像和昵称）', value: 'snsapi_userinfo' },
  { label: 'snsapi_base（只获取 openid）', value: 'snsapi_base' },
]

function resetReactive<T extends Record<string, any>>(target: T, value: T) {
  Object.keys(target).forEach(key => {
    delete target[key]
  })
  Object.assign(target, value)
}

async function loadSettingJSON<T>(key: string, fallback: T): Promise<T> {
  try {
    const res = await request.get(`/settings/${key}`)
    if (!res.data?.value) return fallback
    return { ...fallback, ...JSON.parse(res.data.value) }
  } catch {
    return fallback
  }
}

function removeUrlFileExt<T extends Record<string, any>>(value: T): T {
  const { urlFileExt: _urlFileExt, ...rest } = value
  return rest as T
}

function optionCount(value: Record<string, any> | undefined | null) {
  return value && typeof value === 'object' ? Object.keys(value).length : 0
}

function printerKey(printer: PrinterItem) {
  return `${printer.driver_name || printer.printer_name || 'printer'}-${printer.port || ''}-${printer.ip_addr || ''}`
}

function printerStatusColor(printer: PrinterItem) {
  if (printer.status_level === 'online') return 'green'
  if (printer.status_level === 'busy') return 'blue'
  if (printer.status_level === 'warning') return 'orange'
  return 'default'
}

function resetPrinterInfo(next?: Partial<LankuoPrinterInfo>) {
  Object.assign(printerInfo, {
    configured: false,
    printers: [],
    online_printers: [],
    selected_printer: null,
    selected_model: '',
    printer_params: {},
    params_cached: false,
    params_cached_at: null,
    media_type_options: [],
    paper_options: [],
    ...next,
  })
  selectedPrinterKey.value = next?.selected_printer ? printerKey(next.selected_printer) : ''
  mediaTypeOptions.value = next?.media_type_options || []
}

async function loadPrinterInfo(refresh = false, printerModel?: string) {
  if (!printConfig.ApiKey || !printConfig.deviceId || !printConfig.deviceKey) {
    resetPrinterInfo()
    printerInfoError.value = '请先配置 ApiKey、deviceId 和 deviceKey'
    return
  }

  loadingPrinterInfo.value = true
  printerInfoError.value = ''
  try {
    const res = await request.get('/settings/lankuo/printers', {
      params: {
        printer_model: printerModel || printConfig.printerModel || undefined,
        refresh,
      },
    })
    resetPrinterInfo(res.data)
    const selected = res.data?.selected_printer
    if (selected?.driver_name) {
      printConfig.printerModel = selected.driver_name
      printConfig.devicePort = String(selected.port === 631 ? 1 : selected.port || printConfig.devicePort || '1')
      if (selected.ip_addr) printConfig.targetIp = selected.ip_addr
    }
    if (res.data?.message) {
      printerInfoError.value = res.data.message
    }
  } catch (error: any) {
    resetPrinterInfo()
    printerInfoError.value = error?.response?.data?.detail || '获取打印机信息失败'
  } finally {
    loadingPrinterInfo.value = false
  }
}

async function selectPrinter(printer: PrinterItem) {
  selectedPrinterKey.value = printerKey(printer)
  printConfig.printerModel = printer.driver_name || printConfig.printerModel
  printConfig.devicePort = String(printer.port === 631 ? 1 : printer.port || printConfig.devicePort || '1')
  if (printer.ip_addr) printConfig.targetIp = printer.ip_addr
  await loadPrinterInfo(false, printConfig.printerModel)
}

const onProviderChange = () => {
  loadStorageConfig(activeProvider.value)
}

const loadStorageConfig = async (provider: string) => {
  const fallback = defaultStorageConfigs[provider]
  const parsed = await loadSettingJSON<StorageConfig>(`${provider}_config`, fallback)
  const enabled = parsed.enabled ?? Boolean(parsed.bucket)
  resetReactive(storageConfig, { ...fallback, ...parsed, enabled })
}

const loadPrintConfig = async () => {
  const parsed = await loadSettingJSON<LankuoPrintConfig>('lankuo_print_config', defaultPrintConfig)
  const cleaned = removeUrlFileExt(parsed as Record<string, any>) as LankuoPrintConfig
  resetReactive(printConfig, {
    ...defaultPrintConfig,
    ...cleaned,
    provider: 'lankuo',
    providerName: '蓝阔（链科云打印 v3）',
    reportDeviceStatus: cleaned.reportDeviceStatus ?? true,
    reportPrinterStatus: cleaned.reportPrinterStatus ?? true,
  })
  if (activeSettingsTab.value === 'print') {
    await loadPrinterInfo(false)
  }
}

const loadWechatConfig = async () => {
  const parsed = await loadSettingJSON<WechatOfficialConfig>('wechat_official_account_config', defaultWechatConfig)
  resetReactive(wechatConfig, {
    ...defaultWechatConfig,
    ...parsed,
    scope: parsed.scope || 'snsapi_userinfo',
  })
}

const loadWechatPayConfig = async () => {
  try {
    const res = await request.get('/settings/wechat-pay')
    resetReactive(wechatPayConfig, {
      ...defaultWechatPayConfig,
      ...res.data,
      api_key: '',
      api_v3_key: '',
      private_key: '',
    })
  } catch {
    resetReactive(wechatPayConfig, { ...defaultWechatPayConfig })
  }
}

const loadNetworkConfig = async () => {
  try {
    const res = await request.get('/settings/network')
    resetReactive(networkConfig, {
      ...defaultNetworkConfig,
      ...res.data,
      ssl_cert_pem: '',
      ssl_key_pem: '',
    })
  } catch {
    resetReactive(networkConfig, { ...defaultNetworkConfig })
  }
}

const loadPrintClientConfig = async () => {
  try {
    const res = await request.get('/settings/print_client_token')
    printClientToken.value = res.data?.value || ''
  } catch {
    printClientToken.value = ''
  }
}

const readPemFile = async (event: Event, target: 'cert' | 'key') => {
  const input = event.target as HTMLInputElement
  const file = input.files?.[0]
  if (!file) return
  const text = await file.text()
  if (target === 'cert') {
    networkConfig.ssl_cert_pem = text
  } else {
    networkConfig.ssl_key_pem = text
  }
}

const applyNetworkUrls = () => {
  const notify = networkConfig.wechat_pay_notify_url || derivedNotifyUrl.value
  const refund = networkConfig.wechat_pay_refund_notify_url || derivedRefundNotifyUrl.value
  if (!notify) {
    message.warning('请先设置域名或 Base URL')
    return
  }
  wechatPayConfig.notify_url = notify
  wechatPayConfig.refund_notify_url = refund
  activeSettingsTab.value = 'wechat-pay'
  onSettingsTabChange('wechat-pay')
  message.success('已填入微信支付回调地址')
}

const saveNetworkConfig = async () => {
  savingNetwork.value = true
  try {
    const res = await request.put('/settings/network', {
      domain: networkConfig.domain,
      base_url: networkConfig.base_url,
      ssl_enabled: networkConfig.ssl_enabled,
      force_https: networkConfig.force_https,
      ssl_cert_pem: networkConfig.ssl_cert_pem || undefined,
      ssl_key_pem: networkConfig.ssl_key_pem || undefined,
    })
    resetReactive(networkConfig, {
      ...defaultNetworkConfig,
      ...res.data,
      ssl_cert_pem: '',
      ssl_key_pem: '',
    })
    message.success('网络设置已保存')
  } catch (error: any) {
    message.error(error?.response?.data?.detail || '保存网络设置失败')
  } finally {
    savingNetwork.value = false
  }
}

const saveStorageConfig = async () => {
  savingStorage.value = true
  try {
    await request.put(`/settings/${activeProvider.value}_config`, {
      value: JSON.stringify({ ...storageConfig }),
    })
    message.success('云存储配置已保存')
  } catch {
    message.error('保存云存储配置失败')
  } finally {
    savingStorage.value = false
  }
}

const savePrintConfig = async () => {
  savingPrint.value = true
  try {
    await request.put('/settings/lankuo_print_config', {
      value: JSON.stringify(removeUrlFileExt({ ...printConfig })),
    })
    message.success('云打印配置已保存')
  } catch {
    message.error('保存云打印配置失败')
  } finally {
    savingPrint.value = false
  }
}

const saveWechatConfig = async () => {
  savingWechat.value = true
  try {
    await request.put('/settings/wechat_official_account_config', {
      value: JSON.stringify({ ...wechatConfig }),
    })
    message.success('微信服务号配置已保存')
  } catch {
    message.error('保存微信服务号配置失败')
  } finally {
    savingWechat.value = false
  }
}

const saveWechatPayConfig = async () => {
  savingWechatPay.value = true
  try {
    await request.put('/settings/wechat-pay', {
      enabled: wechatPayConfig.enabled,
      appid: wechatPayConfig.appid,
      mchid: wechatPayConfig.mchid,
      merchant_serial_no: wechatPayConfig.merchant_serial_no,
      notify_url: wechatPayConfig.notify_url,
      refund_notify_url: wechatPayConfig.refund_notify_url,
      description: wechatPayConfig.description,
      api_key: wechatPayConfig.api_key || undefined,
      api_v3_key: wechatPayConfig.api_v3_key || undefined,
      private_key: wechatPayConfig.private_key || undefined,
    })
    message.success('微信支付配置已保存')
    await loadWechatPayConfig()
  } catch {
    message.error('保存微信支付配置失败')
  } finally {
    savingWechatPay.value = false
  }
}

const savePrintClientConfig = async () => {
  savingPrintClient.value = true
  try {
    await request.put('/settings/print_client_token', {
      value: printClientToken.value,
    })
    message.success('本地打印客户端密钥已保存')
  } catch {
    message.error('保存本地打印客户端密钥失败')
  } finally {
    savingPrintClient.value = false
  }
}

const testConnection = async () => {
  testingStorage.value = true
  try {
    const res = await request.post('/settings/storage/test', { provider: activeProvider.value })
    if (res.data.success) {
      message.success('连接测试成功')
    } else {
      message.error(`连接失败：${res.data.message}`)
    }
  } catch {
    message.error('连接测试失败')
  } finally {
    testingStorage.value = false
  }
}

const providers = ['aliyun', 'tencent', 'qiniu']

const detectProvider = async (): Promise<string> => {
  for (const provider of providers) {
    try {
      const res = await request.get(`/settings/${provider}_config`)
      if (res.data?.value) {
        const parsed = JSON.parse(res.data.value)
        const enabled = parsed.enabled ?? Boolean(parsed.bucket)
        if (enabled && parsed.bucket) return provider
      }
    } catch {
      // keep scanning
    }
  }
  return 'aliyun'
}

watch(activeSettingsTab, value => {
  if (value === 'print') {
    loadPrinterInfo(false)
  }
})

onMounted(async () => {
  const detected = await detectProvider()
  activeProvider.value = detected
  await Promise.all([
    loadStorageConfig(detected),
    loadPrintConfig(),
    loadWechatConfig(),
    loadNetworkConfig(),
    loadWechatPayConfig(),
    loadPrintClientConfig(),
  ])
})
</script>

<style scoped>
.settings-page {
  max-width: 1180px;
}

.settings-header {
  display: flex;
  align-items: flex-end;
  justify-content: space-between;
  margin-bottom: 20px;
}

.settings-header h2 {
  margin: 0 0 4px;
  font-size: 24px;
  font-weight: 650;
  color: #202124;
}

.settings-header p {
  margin: 0;
  color: #6b7280;
}

.settings-tabs-card {
  border-radius: 8px;
  background: #fff;
  box-shadow: 0 10px 28px rgba(24, 32, 54, 0.08);
}

.settings-tabs :deep(.ant-tabs-nav) {
  margin-bottom: 22px;
}

.tab-panel-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
  margin-bottom: 18px;
  padding-bottom: 14px;
  border-bottom: 1px solid #eef1f5;
}

.card-title {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  color: #111827;
  font-size: 16px;
  font-weight: 650;
}

.settings-form {
  max-width: 980px;
}

.print-config-layout {
  display: grid;
  grid-template-columns: minmax(0, 1fr) 340px;
  gap: 22px;
  align-items: start;
}

.print-form-column {
  min-width: 0;
}

.printer-inspector {
  position: sticky;
  top: 18px;
  padding: 16px;
  border: 1px solid #edf0f5;
  border-radius: 8px;
  background: #fbfcfe;
}

.printer-inspector-head {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 12px;
  margin-bottom: 14px;
}

.inspector-title {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  color: #111827;
  font-size: 15px;
  font-weight: 650;
}

.inspector-subtitle {
  margin-top: 4px;
  color: #6b7280;
  font-size: 12px;
}

.printer-alert,
.printer-empty {
  margin: 10px 0;
}

.printer-list {
  display: grid;
  gap: 8px;
  margin-bottom: 14px;
}

.printer-row {
  display: flex;
  width: 100%;
  align-items: center;
  justify-content: space-between;
  gap: 10px;
  padding: 10px 11px;
  border: 1px solid #e6eaf0;
  border-radius: 8px;
  background: #fff;
  color: #111827;
  cursor: pointer;
  text-align: left;
}

.printer-row.active {
  border-color: #1677ff;
  box-shadow: 0 0 0 2px rgba(22, 119, 255, 0.08);
}

.printer-row strong,
.printer-row small {
  display: block;
}

.printer-row strong {
  font-size: 13px;
  line-height: 1.35;
}

.printer-row small {
  margin-top: 3px;
  color: #6b7280;
  font-size: 12px;
  line-height: 1.25;
  word-break: break-word;
}

.printer-desc {
  margin-bottom: 14px;
}

.printer-params {
  padding-top: 12px;
  border-top: 1px solid #edf0f5;
}

.params-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 10px;
  font-size: 13px;
  font-weight: 650;
}

.params-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 8px;
}

.params-grid div {
  padding: 9px;
  border-radius: 8px;
  background: #fff;
}

.params-grid span,
.params-grid strong {
  display: block;
}

.params-grid span {
  color: #6b7280;
  font-size: 12px;
}

.params-grid strong {
  margin-top: 3px;
  color: #111827;
  font-size: 15px;
}

.media-options {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
  margin-top: 12px;
}

.card-actions {
  margin-top: 4px;
  padding-top: 16px;
  border-top: 1px solid #f0f0f0;
}

.info-alert {
  margin-bottom: 18px;
}

.form-section {
  margin-bottom: 22px;
}

.section-title {
  margin-bottom: 12px;
  color: #111827;
  font-size: 15px;
  font-weight: 650;
}

@media (max-width: 1180px) {
  .print-config-layout {
    grid-template-columns: 1fr;
  }

  .printer-inspector {
    position: static;
  }
}
</style>
